import sys
import os
import pytest
from pathlib import Path
from src.extractions.e1_notebooks_and_cells import find_notebooks
from src.helpers.h1_utils import SafeSession

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.consts as consts
from src.db.database import Repository
from tests.database_test import connection, session
from tests.factories.models_test import RepositoryFactory
import src.extractions.e1_notebooks_and_cells as e1


class TestH2ScripHelpersFilterRepositories:


    def test_filter_all(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        assert len(session.query(Repository).all()) == 1

        file1_relative_path = 'file.ipynb'
        file2_relative_path = 'to/file.ipynb'
        file3_relative_path = 'file.ipynb_checkpoints'
        def mock_find_files(path, pattern):
            return [Path(f'{repository.path}/{file1_relative_path}'),
                    Path(f'{repository.path}/{file2_relative_path}'),
                    Path(f'{repository.path}/{file3_relative_path}')]
        monkeypatch.setattr(e1, 'find_files', mock_find_files)

        notebooks = e1.find_notebooks(session, repository)
        assert file1_relative_path in notebooks
        assert file2_relative_path in notebooks
        assert file3_relative_path not in notebooks
        assert repository.notebooks_count == 2

    def test_process_notebooks(self, session):
        session =  SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        assert len(session.query(Repository).all()) == 1
        repository_notebooks_names = ['file.ipynb', 'to/file.ipynb']

        count, repository = e1.process_notebooks(session, repository, repository_notebooks_names)


        print("a")
