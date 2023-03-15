import sys
import os
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.consts as consts
import src.extractions.e2_python_files as e2
from src.db.database import Repository
from src.config import Path

from tests.database_config import connection, session
from tests.factories.models_test import RepositoryFactory


class TestE2PythonFilesFindPythonFiles:
    def test_find_python_files(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        assert len(session.query(Repository).all()) == 1

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

        python_files = e2.find_python_files(repository)
        assert file1_relative_path in python_files
        assert file2_relative_path in python_files
        assert file3_relative_path not in python_files
        assert file4_relative_path not in python_files


class TestE2PythonFilesProcessRepository:
    def test_process_repository_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        assert repository.python_files_count is None

        monkeypatch.setattr(e2, 'find_python_files', lambda _repository: ['test.py'])
        monkeypatch.setattr(e2, 'process_python_files',
                            lambda _session, _repository,
                                   _python_files_names, count: (1, True))
        output = e2.process_repository(session, repository)

        assert output == "done"
        assert repository.processed == consts.R_P_EXTRACTION
        assert session.query(Repository).all()[0].python_files_count == 1

    def test_process_repository_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        assert repository.python_files_count is None

        monkeypatch.setattr(e2, 'find_python_files', lambda _repository: ['test.py'])
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

        monkeypatch.setattr(e2, 'find_python_files', lambda _repository: ['test.py'])
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

        monkeypatch.setattr(e2, 'find_python_files', lambda _repository: ['test.py'])
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
    def test_process_python_files(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_files_names = ['test.py']
        count=0
        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)

        assert count == 1
        assert no_errors is True

    def test_process_python_files(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_files_names = ['test.py']
        count=0
        count, no_errors = e2.process_python_files(session, repository, python_files_names, count)

        assert count == 1
        assert no_errors is True