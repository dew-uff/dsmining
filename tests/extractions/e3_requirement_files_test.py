import sys
import os

from unittest.mock import mock_open

from tests.factories.models import PythonFileFactory
from tests.test_helpers.h1_stubs import stub_unzip, stub_unzip_failed

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.consts as consts
import src.extractions.e3_requirement_files as e3
from src.db.database import Repository, PythonFile
from src.config import Path
from tests.database_config import connection, session
from tests.factories.models import RepositoryFactory


class TestE3RequiremtFilesFindRequirements:
    def test_find_requirements(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()

        file1_relative_path = 'setup.py'
        file2_relative_path = 'requirements.txt'
        file3_relative_path = 'Pipfile'
        file4_relative_path = 'Pipfile.lock'
        def mock_find_requirement_files(path, pattern):
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
        def mock_find_requirement_files(path, pattern):
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
        assert repository.processed == consts.R_UNAVAILABLE_FILES