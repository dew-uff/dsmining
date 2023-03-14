import shutil
import sys
import os
import pytest
from pathlib import Path
import time
from src.config import SELECTED_REPOS_DIR, TEST_REPOS_DIR, LOGS_DIR
from src.extractions.e1_notebooks_and_cells import find_notebooks
from src.helpers.h1_utils import SafeSession
from tests.test_helpers.h1_extraction_helpers import mock_load_notebook, mock_load_notebook_error

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.consts as consts
from src.db.database import Repository, Notebook, Cell
from tests.database_test import connection, session
from tests.factories.models_test import RepositoryFactory, NotebookFactory
import src.extractions.e1_notebooks_and_cells as e1
from src.helpers.h1_utils import timeout

class TestE1NotebooksAndCellsFindNotebooks:
    def test_find_notebooks(self, session, monkeypatch):
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

class TestE1NotebooksAndCellsProcessoNotebook:
    def test_process_notebooks(self, session, monkeypatch):
        safe_session =  SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        repository_notebooks_names = ['file.ipynb']

        if not os.path.exists(repository.path):
            os.makedirs(repository.path)

        monkeypatch.setattr(e1, 'load_notebook', mock_load_notebook)

        count, repository = e1.process_notebooks(safe_session, repository, repository_notebooks_names)
        safe_session.commit()
        assert count == 1
        assert  (session.query(Notebook).count()) == 1
        assert  (session.query(Cell).count()) == 1

        notebook = session.query(Notebook).all()[0]
        cell = session.query(Cell).all()[0]

        assert notebook.repository_id == repository.id
        assert cell.notebook_id == notebook.id

        if os.path.exists(TEST_REPOS_DIR):
            shutil.rmtree(TEST_REPOS_DIR)

    def test_process_notebooks_no_name(self, session):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        assert len(session.query(Repository).all()) == 1
        repository_notebooks_names = ['']
        count, repository = e1.process_notebooks(safe_session, repository, repository_notebooks_names)

        assert count == 0
        assert  (session.query(Notebook).count()) == 0
        assert  (session.query(Cell).count()) == 0


    def test_process_notebooks_no_none_stoped(self, session):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id,
                                                   processed = consts.N_STOPPED)
        created = notebook.created_at
        if not os.path.exists(repository.path):
            os.makedirs(repository.path)


        e1.process_notebooks(safe_session, repository, [notebook.name])
        safe_session.commit()

        if os.path.exists(TEST_REPOS_DIR):
            shutil.rmtree(TEST_REPOS_DIR)

        assert created != session.query(Notebook).all()[0].created_at

    def test_process_notebooks_no_none_generic_load(self, session, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id,
                                                   processed=consts.N_GENERIC_LOAD_ERROR)

        e1.process_notebooks(safe_session, repository, [notebook.name])
        captured = capsys.readouterr()
        assert "Notebook already exists. Delete from DB" in captured.out
        assert os.path.exists(str(LOGS_DIR)+"/todo_delete")
        os.remove(str(LOGS_DIR)+"/todo_delete")

    def test_process_notebooks_no_path_done(self, session, monkeypatch):
        def mock_unzip(session_, repository_):
            return "done"
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        repository_notebooks_names = ['file.ipynb']
        monkeypatch.setattr(e1, 'load_notebook', mock_load_notebook)
        monkeypatch.setattr(e1, 'unzip_repository', mock_unzip)
        count, repository = e1.process_notebooks(safe_session, repository, repository_notebooks_names)

        safe_session.commit()
        assert count == 1
        assert (session.query(Notebook).count()) == 1
        assert (session.query(Cell).count()) == 1

    def test_process_notebooks_no_path_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        repository_notebooks_names = ['file.ipynb']
        monkeypatch.setattr(e1, 'load_notebook', mock_load_notebook)

        e1.process_notebooks(safe_session, repository, repository_notebooks_names)
        captured = capsys.readouterr()
        assert "Failed to load notebook" in captured.out

    def test_process_notebooks_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        repository_notebooks_names = ['file.ipynb']

        if not os.path.exists(repository.path):
            os.makedirs(repository.path)

        monkeypatch.setattr(e1, 'load_notebook', mock_load_notebook_error)

        count, repository = e1.process_notebooks(safe_session, repository, repository_notebooks_names)

        captured = capsys.readouterr()
        assert "Failed to load notebook" in captured.out
        assert repository.processed == consts.R_N_ERROR

class Test1NotebooksAndCellsProcessRepository:
    def test_process_notebooks(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create()
        assert  repository.notebooks_count is None

        repository.notebooks_count=1
        monkeypatch.setattr(e1, 'find_notebooks', lambda _session, _repository: [])
        monkeypatch.setattr(e1, 'process_notebooks',
                            lambda _session, _repository, _repository_notebooks_names: (1, repository))
        output = e1.process_repository(safe_session, repository)

        assert output == "done"
        assert safe_session.query(Repository).all()[0].notebooks_count == 1

    def test_process_notebooks_already_processed(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(
            processed=consts.R_N_EXTRACTION)

        output = e1.process_repository(safe_session, repository)

        assert output == "already processed"

    def test_process_notebooks_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(processed=consts.R_N_ERROR,
                                                            notebooks_count=1)

        monkeypatch.setattr(e1, 'find_notebooks', lambda _session, _repository: [])
        monkeypatch.setattr(e1, 'process_notebooks',
                            lambda _session, _repository, _repository_notebooks_names: (1, repository))
        output = e1.process_repository(safe_session, repository)
        repository = safe_session.query(Repository).all()[0]

        assert repository.processed == consts.R_N_EXTRACTION
        captured = capsys.readouterr()
        assert "retrying to process" in captured.out
        assert output == "done"


    def test_process_notebooks_no_status_extracted(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(processed=consts.R_N_ERROR,
                                                            notebooks_count=1)

        monkeypatch.setattr(e1, 'find_notebooks', lambda _session, _repository: [])
        monkeypatch.setattr(e1, 'process_notebooks',
                            lambda _session, _repository, _repository_notebooks_names: (1, repository))
        monkeypatch.setattr(safe_session, 'commit', lambda : (None, 'error 1'))

        output = e1.process_repository(safe_session, repository)
        repository = safe_session.query(Repository).all()[0]
        assert "failed due 'error 1'" in output
        assert repository.processed == consts.R_N_ERROR
