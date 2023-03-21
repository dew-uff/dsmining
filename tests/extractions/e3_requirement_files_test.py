import os
import sys

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path:
    sys.path.append(src)

import chardet
import src.consts as consts
import src.extractions.e3_requirement_files as e3

from unittest.mock import mock_open
from src.db.database import Repository, PythonFile, RequirementFile
from src.config import Path
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory
from tests.factories.models import RequirementFileFactory
from tests.test_helpers.h1_stubs import stub_unzip, stub_unzip_failed, REQUIREMENTS_TXT
from src.states import *


class TestE3RequiremtFilesFindRequirements:
    def test_find_requirements(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()

        file1_relative_path = 'setup.py'
        file2_relative_path = 'requirements.txt'
        file3_relative_path = 'Pipfile'
        file4_relative_path = 'Pipfile.lock'

        def mock_find_requirement_files(path, pattern):  # noqa: F841
            return [[Path(f'{file1_relative_path}')],
                    [Path(f'{file2_relative_path}')],
                    [Path(f'{file3_relative_path}')],
                    [Path(f'{file4_relative_path}')]]

        monkeypatch.setattr(e3, 'find_files_in_path', mock_find_requirement_files)
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        setups, requirements, pipfiles, pipfile_locks = e3.find_requirements(session, repository)

        assert file1_relative_path == str(setups[0])
        assert file2_relative_path == str(requirements[0])
        assert file3_relative_path == str(pipfiles[0])
        assert file4_relative_path == str(pipfile_locks[0])

        assert repository.setups_count == 1
        assert repository.requirements_count == 1
        assert repository.pipfiles_count == 1
        assert repository.pipfile_locks_count == 1

    def test_find_requirements_zip_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()

        file1_relative_path = 'setup.py'
        file2_relative_path = 'requirements.txt'
        file3_relative_path = 'Pipfile'
        file4_relative_path = 'Pipfile.lock'

        def mock_find_requirement_files(path, pattern):  # noqa: F841
            return [[Path(f'{file1_relative_path}')],
                    [Path(f'{file2_relative_path}')],
                    [Path(f'{file3_relative_path}')],
                    [Path(f'{file4_relative_path}')]]

        monkeypatch.setattr(Path, 'exists', lambda path: False)
        monkeypatch.setattr(e3, 'unzip_repository', stub_unzip)
        monkeypatch.setattr(e3, 'find_files_in_path', mock_find_requirement_files)

        setups, requirements, pipfiles, pipfile_locks = e3.find_requirements(session, repository)

        assert file1_relative_path == str(setups[0])
        assert file2_relative_path == str(requirements[0])
        assert file3_relative_path == str(pipfiles[0])
        assert file4_relative_path == str(pipfile_locks[0])

        assert repository.setups_count == 1
        assert repository.requirements_count == 1
        assert repository.pipfiles_count == 1
        assert repository.pipfile_locks_count == 1

    def test_find_requirements_zip_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()

        monkeypatch.setattr(Path, 'exists', lambda path: False)
        monkeypatch.setattr(e3, 'unzip_repository', stub_unzip_failed)

        setups, requirements, pipfiles, pipfile_locks = e3.find_requirements(session, repository)
        assert setups == []
        assert requirements == []
        assert pipfiles == []
        assert pipfile_locks == []
        assert repository.state == REP_UNAVAILABLE_FILES


class TestE3RequiremtFilesProcessRepository:
    def test_process_repository_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)
        assert repository.python_files_count is None

        file = [Path('setup.py')]
        monkeypatch.setattr(e3, 'find_requirements',
                            lambda _session, _repository: [[file], [], [], []])
        monkeypatch.setattr(e3, 'process_requirement_files',
                            lambda _session, _repository, _python_files_names, count: True)
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        output = e3.process_repository(session, repository)

        assert output == "done"
        assert repository.state == REP_REQ_FILE_EXTRACTED

    def test_process_repository_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)

        file = [Path('setup.py')]
        monkeypatch.setattr(e3, 'find_requirements',
                            lambda _session, _repository: [[file], [], [], []])
        monkeypatch.setattr(e3, 'process_requirement_files',
                            lambda _session, _repository, _python_files_names, count: False)
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        output = e3.process_repository(session, repository)

        assert output == "done"
        assert repository.state == REP_REQ_FILE_ERROR

    def test_process_repository_retry_success(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_REQ_FILE_ERROR)

        file = [Path('setup.py')]
        monkeypatch.setattr(e3, 'find_requirements',
                            lambda _session, _repository: [[file], [], [], []])
        monkeypatch.setattr(e3, 'process_requirement_files',
                            lambda _session, _repository, _python_files_names, count: True)
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        output = e3.process_repository(session, repository, retry=True)

        assert repository.state == REP_REQ_FILE_EXTRACTED
        captured = capsys.readouterr()
        assert "retrying to process" in captured.out
        assert output == "done"

    def test_process_repository_retry_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_REQ_FILE_ERROR)
        assert repository.python_files_count is None

        file = [Path('setup.py')]
        monkeypatch.setattr(e3, 'find_requirements',
                            lambda _session, _repository: [[file], [], [], []])
        monkeypatch.setattr(e3, 'process_requirement_files',
                            lambda _session, _repository, _python_files_names, count: False)
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        output = e3.process_repository(session, repository, retry=True)

        assert output == "done"
        assert repository.state == REP_REQ_FILE_ERROR
        assert session.query(Repository).first().python_files_count is None

    def test_process_repository_not_retry(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_REQ_FILE_ERROR)

        output = e3.process_repository(session, repository)

        assert output == "already processed"

    def test_process_repository_already_processed(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            state=REP_REQ_FILE_EXTRACTED)

        output = e3.process_repository(session, repository)

        assert output == "already processed"

    def test_process_repository_state_after(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            state=REP_FINISHED)

        output = e3.process_repository(session, repository)

        assert output == "already processed"

    def test_process_repository_state_before(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            state=REP_N_EXTRACTED)

        output = e3.process_repository(session, repository)

        assert "wrong script order" in output


class TestE3RequiremtFilesProcessRequirementFiles:
    def test_process_requirement_files_sucess(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=REQUIREMENTS_TXT))
        reqformat = 'requirements.txt'
        req_names = [Path('requirements.txt')]

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()

        requirement_file = session.query(RequirementFile).first()

        assert no_errors is True
        assert requirement_file.repository_id == repository.id
        assert requirement_file.state == REQ_FILE_LOADED
        assert requirement_file.content == REQUIREMENTS_TXT.decode('ascii')

    def test_process_requirement_files_path_zip(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)
        reqformat = 'requirements.txt'
        req_names = [Path('requirements.txt')]
        monkeypatch.setattr(Path, 'exists', lambda path: False)
        monkeypatch.setattr(e3, 'unzip_repository', stub_unzip)
        monkeypatch.setattr('builtins.open', mock_open(read_data=REQUIREMENTS_TXT))

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()

        requirement_file = session.query(RequirementFile).first()

        captured = capsys.readouterr()

        assert no_errors is True
        assert requirement_file.repository_id == repository.id
        assert requirement_file.state == REQ_FILE_LOADED
        assert requirement_file.content == REQUIREMENTS_TXT.decode('ascii')
        assert 'Unzipping repository' in captured.out

    def test_process_requirement_files_path_error(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)
        reqformat = 'requirements.txt'
        req_names = [Path('requirements.txt')]
        monkeypatch.setattr(Path, 'exists', lambda path: False)

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()

        query = session.query(RequirementFile).all()
        captured = capsys.readouterr()

        assert no_errors is False
        assert query == []
        assert 'Failed to load' in captured.out

    def test_process_requirement_files_no_name(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create()
        reqformat = 'requirements.txt'
        req_names = ['']
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()
        query = session.query(RequirementFile).all()

        assert query == []
        assert no_errors is True

    def test_process_requirement_files_already_exists_with_error(self, session, monkeypatch, capsys):
        name = 'requirements.txt'
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)
        reqformat = 'requirements.txt'
        req_names = [Path(name)]
        python_file = RequirementFileFactory(session).create(repository_id=repository.id,
                                                             name=name,
                                                             state=REQ_FILE_L_ERROR)
        initial_created_at = python_file.created_at

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=REQUIREMENTS_TXT))

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()

        requirement_file_result = session.query(RequirementFile).first()

        assert requirement_file_result.repository_id == repository.id
        assert requirement_file_result.state == REQ_FILE_LOADED
        assert initial_created_at != requirement_file_result.created_at
        assert no_errors is True

    def test_process_requirement_files_already_exists_loaded(self, session, monkeypatch, capsys):
        name = 'requirements.txt'
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)
        reqformat = 'requirements.txt'
        req_names = [Path(name)]
        python_file = RequirementFileFactory(session).create(repository_id=repository.id,
                                                             name=name,
                                                             state=REQ_FILE_LOADED)
        initial_created_at = python_file.created_at

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=REQUIREMENTS_TXT))

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()
        captured = capsys.readouterr()
        requirement_file_result = session.query(RequirementFile).first()

        assert requirement_file_result.repository_id == repository.id
        assert requirement_file_result.state == REQ_FILE_LOADED
        assert initial_created_at == requirement_file_result.created_at
        assert "Python File already processed" in captured.out
        assert no_errors is True

    def test_process_requirement_files_no_codec(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)
        reqformat = 'requirements.txt'
        req_names = [Path('requirements.txt')]
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=REQUIREMENTS_TXT))
        monkeypatch.setattr(chardet, 'detect', lambda content: {'encoding': None, 'confidence': 0.0, 'language': None})

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()
        requirement_file = session.query(RequirementFile).first()
        captured = capsys.readouterr()

        assert no_errors is True
        assert requirement_file.repository_id == repository.id
        assert requirement_file.state == REQ_FILE_L_ERROR
        assert 'codec not detected' in captured.out

    def test_process_requirement_files_invalid_codec(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)
        reqformat = 'requirements.txt'
        req_names = [Path('requirements.txt')]
        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=REQUIREMENTS_TXT))
        monkeypatch.setattr(chardet, 'detect',
                            lambda content: {'encoding': 'error', 'confidence': 0.0, 'language': None})

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()
        requirement_file = session.query(RequirementFile).first()
        captured = capsys.readouterr()

        assert no_errors is True
        assert requirement_file.repository_id == repository.id
        assert requirement_file.state == REQ_FILE_L_ERROR
        assert 'invalid codec' in captured.out

    def test_process_requirement_files_null_byte(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=b"test\0test\n"))
        reqformat = 'requirements.txt'
        req_names = [Path('requirements.txt')]

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()

        requirement_file = session.query(RequirementFile).first()

        assert no_errors is True
        assert requirement_file.repository_id == repository.id
        assert requirement_file.state == REQ_FILE_LOADED
        assert requirement_file.content == "test\ntest\n"

    def test_process_requirement_files_empty(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_PF_EXTRACTED)

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=b""))
        reqformat = 'requirements.txt'
        req_names = [Path('requirements.txt')]

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()
        captured = capsys.readouterr()
        requirement_file = session.query(RequirementFile).first()

        assert no_errors is True
        assert requirement_file.repository_id == repository.id
        assert requirement_file.state == REQ_FILE_EMPTY
        assert "is empty" in captured.out

    def test_process_requirement_files_IOError(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create()

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr('builtins.open', mock_open(read_data=REQUIREMENTS_TXT))
        reqformat = 'requirements.txt'
        req_names = [Path('requirements.txt')]

        def raise_error(text, error): raise FileNotFoundError  # noqa: F841

        m = mock_open()
        m.side_effect = raise_error
        monkeypatch.setattr('builtins.open', m)

        no_errors = e3.process_requirement_files(session, repository, req_names, reqformat)
        session.commit()
        captured = capsys.readouterr()
        requirement_file = session.query(RequirementFile).first()

        assert no_errors is True
        assert requirement_file.repository_id == repository.id
        assert requirement_file.state == REQ_FILE_L_ERROR
        assert 'Failed to load' in captured.out
