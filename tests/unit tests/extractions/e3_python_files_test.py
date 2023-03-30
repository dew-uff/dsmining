import sys
import os

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

from unittest.mock import mock_open  # noqa

from src.config.consts import Path
from src.config.states import *
from src.db.database import Repository, PythonFile
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory
from tests.factories.models import PythonFileFactory
from tests.stubs.others import stub_unzip, stub_unzip_failed

import src.extractions.e3_python_files as e3


class TestPythonFilesFindPythonFiles:
    def test_find_python_files(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()

        file1_relative_path = 'test.py'
        file2_relative_path = 'to/file.py'
        file3_relative_path = 'setup.py'
        file4_relative_path = 'abc123/setup.py'

        def mock_find_python_files(path, pattern):  # noqa: F841
            return [Path('{}/{}'.format(repository.path, file1_relative_path)),
                    Path('{}/{}'.format(repository.path, file2_relative_path)),
                    Path('{}/{}'.format(repository.path, file3_relative_path)),
                    Path('{}/{}'.format(repository.path, file4_relative_path))]

        monkeypatch.setattr(e3, 'find_files', mock_find_python_files)
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        python_files = e3.find_python_files(session, repository)
        assert file1_relative_path in python_files
        assert file2_relative_path in python_files
        assert file3_relative_path not in python_files
        assert file4_relative_path not in python_files

    def test_find_python_files_zip_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()

        file1_relative_path = 'test.py'
        file2_relative_path = 'to/file.py'
        file3_relative_path = 'setup.py'
        file4_relative_path = 'abc123/setup.py'

        def mock_find_python_files(path, pattern):  # noqa: F841
            return [Path('{}/{}'.format(repository.path, file1_relative_path)),
                    Path('{}/{}'.format(repository.path, file2_relative_path)),
                    Path('{}/{}'.format(repository.path, file3_relative_path)),
                    Path('{}/{}'.format(repository.path, file4_relative_path))]

        monkeypatch.setattr(e3, 'find_files', mock_find_python_files)
        monkeypatch.setattr(Path, 'exists', lambda path: False)
        monkeypatch.setattr(e3, 'unzip_repository', stub_unzip)

        python_files = e3.find_python_files(session, repository)
        assert file1_relative_path in python_files
        assert file2_relative_path in python_files
        assert file3_relative_path not in python_files
        assert file4_relative_path not in python_files

    def test_find_python_files_zip_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()

        monkeypatch.setattr(Path, 'exists', lambda path: False)
        monkeypatch.setattr(e3, 'unzip_repository', stub_unzip_failed)

        python_files = e3.find_python_files(session, repository)
        assert python_files == []
        assert repository.state == REP_UNAVAILABLE_FILES


class TestPythonFilesProcessRepository:
    def test_process_repository_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_N_EXTRACTED)
        assert repository.python_files_count is None

        monkeypatch.setattr(e3, 'find_python_files', lambda _session, _repository: ['test.py'])
        monkeypatch.setattr(e3, 'process_python_files',
                            lambda _session, _repository, _python_files_names, count: 1)
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        output = e3.process_repository(session, repository)

        assert output == "done"
        assert repository.state == REP_PF_EXTRACTED
        assert session.query(Repository).first().python_files_count == 1

    def test_process_repository_unavailable(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_N_EXTRACTED)
        assert repository.python_files_count is None

        def unavailable_files(_session, _repository):
            _repository.state = REP_UNAVAILABLE_FILES
            return []

        monkeypatch.setattr(e3, 'find_python_files', unavailable_files)
        monkeypatch.setattr(e3, 'process_python_files',
                            lambda _session, _repository, _python_files_names, count: 1)
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        output = e3.process_repository(session, repository)

        assert output == "done"
        assert repository.state == REP_UNAVAILABLE_FILES
        assert session.query(PythonFile).count() == 0

    def test_process_repository_already_processed(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            state=REP_PF_EXTRACTED)

        output = e3.process_repository(session, repository)

        assert output == "already processed"

    def test_process_repository_state_after(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            state=REP_REQ_FILE_EXTRACTED)

        output = e3.process_repository(session, repository)

        assert output == "already processed"

    def test_process_repository_state_before(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            state=REP_LOADED)

        output = e3.process_repository(session, repository)

        assert "wrong script order" in output


class TestPythonFilesProcessPythonFiles:
    def test_process_python_files_sucess(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_N_EXTRACTED)
        python_files_names = ['test.py']
        count = 0
        source = 'import matplotlib\nprint("test")\n'
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=source))

        count = e3.process_python_files(session, repository, python_files_names, count)
        session.commit()
        python_file = session.query(PythonFile).first()

        assert count == 1
        assert python_file.repository_id == repository.id
        assert python_file.total_lines == 2
        assert python_file.source == source
        assert python_file.state == PF_LOADED

    def test_process_python_files_no_name(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_N_EXTRACTED)
        python_files_names = ['']
        count = 0
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        count = e3.process_python_files(session, repository, python_files_names, count)
        session.commit()
        query = session.query(PythonFile).all()

        assert count == 0
        assert query == []

    def test_process_python_files_already_exists_with_error(self, session, monkeypatch, capsys):
        """ If python file with error, reprocesses """

        count = 0
        name = "test.py"
        repository = RepositoryFactory(session).create(state=REP_N_EXTRACTED)
        python_files_names = [name]
        python_file = PythonFileFactory(session).create(repository_id=repository.id,
                                                        name=name,
                                                        state=PF_L_ERROR)
        initial_created_at = python_file.created_at

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data="import matplotlib\n"))

        count = e3.process_python_files(session, repository, python_files_names, count)
        session.commit()

        python_file_result = session.query(PythonFile).first()

        assert initial_created_at != python_file_result.created_at
        assert count == 1
        assert python_file_result.state == PF_LOADED

    def test_process_python_files_already_exists_loaded(self, session, monkeypatch, capsys):
        """ If python file with error, reprocesses """

        count = 0
        name = "test.py"
        repository = RepositoryFactory(session).create(state=REP_N_EXTRACTED)
        python_files_names = [name]
        python_file = PythonFileFactory(session).create(repository_id=repository.id,
                                                        name=name,
                                                        state=PF_LOADED)
        initial_created_at = python_file.created_at

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data="import matplotlib\n"))

        count = e3.process_python_files(session, repository, python_files_names, count)
        session.commit()
        captured = capsys.readouterr()
        python_file_result = session.query(PythonFile).first()

        assert initial_created_at == python_file_result.created_at
        assert count == 1
        assert python_file_result.state == PF_LOADED
        assert "Python File already processed" in captured.out

    def test_process_python_files_sucess_empty(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_N_EXTRACTED)
        python_files_names = ['test.py']
        count = 0
        source = ''
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=source))

        count = e3.process_python_files(session, repository, python_files_names, count)
        session.commit()
        python_file = session.query(PythonFile).first()

        assert count == 1
        assert python_file.repository_id == repository.id
        assert python_file.total_lines == 0
        assert python_file.state == PF_EMPTY

    def test_process_python_files_IOError(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_files_names = ['test.py']
        count = 0
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        def raise_error(text): raise FileNotFoundError  # noqa: F841

        m = mock_open()
        m.side_effect = raise_error
        monkeypatch.setattr('builtins.open', m)

        count = e3.process_python_files(session, repository, python_files_names, count)
        session.commit()
        python_file = session.query(PythonFile).first()

        assert count == 1
        assert python_file.repository_id == repository.id
        assert python_file.state == PF_L_ERROR
        assert python_file.source is None
        assert python_file.total_lines is None
