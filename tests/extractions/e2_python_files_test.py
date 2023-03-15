import sys
import os

from unittest.mock import mock_open

from tests.factories.models import PythonFileFactory
from tests.test_helpers.h1_stubs import stub_unzip, stub_unzip_failed

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.consts as consts
import src.extractions.e2_python_files as e2
from src.db.database import Repository, PythonFile
from src.config import Path

from tests.database_config import connection, session
from tests.factories.models import RepositoryFactory


class TestE2PythonFilesFindPythonFiles:
    def test_find_python_files(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()

        file1_relative_path = 'test.py'
        file2_relative_path = 'to/file.py'
        file3_relative_path = 'setup.py'
        file4_relative_path = 'abc123/setup.py'
        def mock_find_python_files(path, pattern):
            return [Path(f'{repository.path}/{file1_relative_path}'),
                    Path(f'{repository.path}/{file2_relative_path}'),
                    Path(f'{repository.path}/{file3_relative_path}'),
                    Path(f'{repository.path}/{file4_relative_path}')]
        monkeypatch.setattr(e2, 'find_files', mock_find_python_files)
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        python_files = e2.find_python_files(session, repository)
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
        def mock_find_python_files(path, pattern):
            return [Path(f'{repository.path}/{file1_relative_path}'),
                    Path(f'{repository.path}/{file2_relative_path}'),
                    Path(f'{repository.path}/{file3_relative_path}'),
                    Path(f'{repository.path}/{file4_relative_path}')]
        monkeypatch.setattr(e2, 'find_files', mock_find_python_files)
        monkeypatch.setattr(Path, 'exists', lambda path: False)
        monkeypatch.setattr(e2, 'unzip_repository', stub_unzip)

        python_files = e2.find_python_files(session, repository)
        assert file1_relative_path in python_files
        assert file2_relative_path in python_files
        assert file3_relative_path not in python_files
        assert file4_relative_path not in python_files

    def test_find_python_files_zip_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()


        monkeypatch.setattr(Path, 'exists', lambda path: False)
        monkeypatch.setattr(e2, 'unzip_repository', stub_unzip_failed)

        python_files = e2.find_python_files(session, repository)
        assert python_files == []
        assert repository.processed == consts.R_UNAVAILABLE_FILES


class TestE2PythonFilesProcessRepository:
    def test_process_repository_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        assert repository.python_files_count is None

        monkeypatch.setattr(e2, 'find_python_files', lambda _session, _repository: ['test.py'])
        monkeypatch.setattr(e2, 'process_python_files',
                            lambda _session, _repository,
                                   _python_files_names, count: (1, True))
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        output = e2.process_repository(session, repository)

        assert output == "done"
        assert repository.processed == consts.R_P_EXTRACTION
        assert session.query(Repository).all()[0].python_files_count == 1

    def test_process_repository_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        assert repository.python_files_count is None

        monkeypatch.setattr(e2, 'find_python_files', lambda _session, _repository: ['test.py'])
        monkeypatch.setattr(e2, 'process_python_files',
                            lambda _session, _repository, _python_files_names, count:
                            (1, False))
        output = e2.process_repository(session, repository)

        assert output == "done"
        assert repository.processed == consts.R_P_ERROR
        assert session.query(Repository).all()[0].python_files_count is None

    def test_process_repository_already_processed(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            processed=consts.R_P_EXTRACTION)

        output = e2.process_repository(session, repository)

        assert output == "already processed"

    def test_process_repository_retry_error_success(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(processed=consts.R_P_ERROR)

        monkeypatch.setattr(e2, 'find_python_files', lambda _session, _repository: ['test.py'])
        monkeypatch.setattr(e2, 'process_python_files',
                            lambda _session, _repository,
                                   _python_files_names, count: (1, True))

        output = e2.process_repository(session, repository, skip_if_error=0)

        assert repository.processed == consts.R_P_EXTRACTION
        captured = capsys.readouterr()
        assert "retrying to process" in captured.out
        assert output == "done"

    def test_process_repository_retry_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(processed = consts.R_P_ERROR)
        assert repository.python_files_count is None

        monkeypatch.setattr(e2, 'find_python_files', lambda _session, _repository: ['test.py'])
        monkeypatch.setattr(e2, 'process_python_files',
                            lambda _session, _repository, _python_files_names, count:
                            (1, False))
        output = e2.process_repository(session, repository, skip_if_error=0)

        assert output == "done"
        assert repository.processed == consts.R_P_ERROR
        assert session.query(Repository).all()[0].python_files_count is None

    def test_process_repository_skip_error(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(processed=consts.R_P_ERROR)

        output = e2.process_repository(session, repository)

        assert output == "already processed"


class TestE2PythonFilesProcessPythonFiles:
    def test_process_python_files_sucess(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_files_names = ['test.py']
        count=0
        source = 'import matplotlib\nprint("test")\n'
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=source))


        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)
        session.commit()
        python_file = session.query(PythonFile).all()[0]

        assert count == 1
        assert no_errors is True
        assert python_file.repository_id == repository.id
        assert python_file.total_lines == 2
        assert python_file.source == source

    def test_process_python_files_sucess_empty_file(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_files_names = ['test.py']
        count=0
        source = ''
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=source))


        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)
        session.commit()
        python_file = session.query(PythonFile).all()[0]

        assert count == 1
        assert no_errors is True
        assert python_file.repository_id == repository.id
        assert python_file.total_lines == 0
        assert python_file.processed == consts.PF_EMPTY

    def test_process_python_files_path_zip(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create()
        python_files_names = ['test.py']
        count=0
        source = 'import matplotlib\nprint("test")\n'
        monkeypatch.setattr(Path, 'exists', lambda path: False)
        monkeypatch.setattr(e2, 'unzip_repository', stub_unzip)
        monkeypatch.setattr('builtins.open', mock_open(read_data=source))


        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)
        session.commit()
        python_file = session.query(PythonFile).all()[0]
        captured = capsys.readouterr()

        assert count == 1
        assert no_errors is True
        assert python_file.repository_id == repository.id
        assert 'Unzipping repository' in captured.out

    def test_process_python_files_path_error(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create()
        python_files_names = ['test.py']
        count=0
        monkeypatch.setattr(Path, 'exists', lambda path: False)


        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)
        session.commit()
        query = session.query(PythonFile).all()
        captured = capsys.readouterr()

        assert count == 0
        assert no_errors is False
        assert query == []
        assert 'Failed to load notebooks' in captured.out

    def test_process_python_files_no_name(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create()
        python_files_names = ['']
        count=0
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)
        session.commit()
        query = session.query(PythonFile).all()

        assert count == 0
        assert query == []
        assert no_errors is True

    def test_process_python_files_already_exists(self, session, monkeypatch, capsys):
        """ If python file with error, reprocesses """

        count = 0
        name = "test.py"
        repository = RepositoryFactory(session).create()
        python_files_names = [name]
        python_file = PythonFileFactory(session).create(repository_id=repository.id,
                                                        name= name,
                                                        processed= consts.PF_ERROR)
        initial_created_at = python_file.created_at


        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data="import matplotlib\n"))

        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)
        session.commit()

        python_file_result = session.query(PythonFile).all()[0]

        assert initial_created_at != python_file_result.created_at
        assert count == 1
        assert no_errors is True

    def test_process_python_files_IOError(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_files_names = ['test.py']
        count = 0
        source = 'import matplotlib\nprint("test")\n'
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        def raise_error(text): raise FileNotFoundError
        m = mock_open()
        m.side_effect = raise_error
        monkeypatch.setattr('builtins.open', m)

        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)
        session.commit()
        python_file = session.query(PythonFile).all()[0]

        assert count == 1
        assert no_errors is True
        assert python_file.repository_id == repository.id
        assert python_file.processed == consts.PF_ERROR
        assert python_file.source is None
        assert python_file.total_lines  is None
