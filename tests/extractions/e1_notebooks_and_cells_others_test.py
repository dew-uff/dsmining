import sys
import os
src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import src.consts as consts
import src.extractions.e1_notebooks_and_cells as e1
from src.db.database import Repository, Notebook, Cell

from src.config import LOGS_DIR, Path
from src.helpers.h1_utils import SafeSession
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory, NotebookFactory
from tests.test_helpers.h1_stubs import stub_load_notebook, stub_load_notebook_error, stub_unzip
from src.states import *


class TestE1NotebooksAndCellsFindNotebooks:
    def test_find_notebooks(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        assert len(session.query(Repository).all()) == 1

        file1_relative_path = 'file.ipynb'
        file2_relative_path = 'to/file.ipynb'
        file3_relative_path = 'file.ipynb_checkpoints'

        def mock_find_files(path, pattern):  # noqa: F841
            return [Path(f'{repository.path}/{file1_relative_path}'),
                    Path(f'{repository.path}/{file2_relative_path}'),
                    Path(f'{repository.path}/{file3_relative_path}')]
        monkeypatch.setattr(e1, 'find_files', mock_find_files)

        notebooks = e1.find_notebooks(session, repository)
        assert file1_relative_path in notebooks
        assert file2_relative_path in notebooks
        assert file3_relative_path not in notebooks
        assert repository.notebooks_count == 2


class TestE1NotebooksAndCellsProcessNotebook:
    def test_process_notebooks(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        repository_notebooks_names = ['file.ipynb']

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr(e1, 'load_notebook', stub_load_notebook)

        count, repository = e1.process_notebooks(safe_session, repository, repository_notebooks_names)
        safe_session.commit()
        assert count == 1
        assert (session.query(Notebook).count()) == 1
        assert (session.query(Cell).count()) == 1

        notebook = session.query(Notebook).first()
        cell = session.query(Cell).first()

        assert notebook.repository_id == repository.id
        assert cell.notebook_id == notebook.id

    def test_process_notebooks_no_name(self, session):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        assert len(session.query(Repository).all()) == 1
        repository_notebooks_names = ['']
        count, repository = e1.process_notebooks(safe_session, repository, repository_notebooks_names)

        assert count == 0
        assert (session.query(Notebook).count()) == 0
        assert (session.query(Cell).count()) == 0

    def test_process_notebooks_no_none_stoped(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id,
                                                   processed=consts.N_STOPPED)
        created = notebook.created_at
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        e1.process_notebooks(safe_session, repository, [notebook.name])
        safe_session.commit()

        assert created != session.query(Notebook).first().created_at

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

        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        repository_notebooks_names = ['file.ipynb']
        monkeypatch.setattr(e1, 'load_notebook', stub_load_notebook)
        monkeypatch.setattr(e1, 'unzip_repository', stub_unzip)
        count, repository = e1.process_notebooks(safe_session, repository, repository_notebooks_names)

        safe_session.commit()
        assert count == 1
        assert (session.query(Notebook).count()) == 1
        assert (session.query(Cell).count()) == 1

    def test_process_notebooks_no_path_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        repository_notebooks_names = ['file.ipynb']
        monkeypatch.setattr(e1, 'load_notebook', stub_load_notebook)

        e1.process_notebooks(safe_session, repository, repository_notebooks_names)
        captured = capsys.readouterr()
        assert "Failed to load" in captured.out

    def test_process_notebooks_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(session).create(notebooks_count=2)
        repository_notebooks_names = ['file.ipynb']

        monkeypatch.setattr(Path, 'exists', lambda path: True)
        monkeypatch.setattr(e1, 'load_notebook', stub_load_notebook_error)

        count, repository = e1.process_notebooks(safe_session, repository, repository_notebooks_names)

        captured = capsys.readouterr()
        assert "Failed to load notebook" in captured.out
        assert repository.state == REP_N_ERROR


class Test1NotebooksAndCellsProcessRepository:
    def test_process_repository_success(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create()
        assert repository.notebooks_count is None

        repository.notebooks_count = 1
        monkeypatch.setattr(e1, 'find_notebooks', lambda _session, _repository: [])
        monkeypatch.setattr(e1, 'process_notebooks',
                            lambda _session, _repository, _repository_notebooks_names: (1, repository))
        output = e1.process_repository(safe_session, repository)

        assert output == "done"
        assert safe_session.query(Repository).first().notebooks_count == 1
        assert repository.state == REP_N_EXTRACTION

    def test_process_repository_error(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create()

        monkeypatch.setattr(e1, 'find_notebooks', lambda _session, _repository: [])
        monkeypatch.setattr(e1, 'process_notebooks',
                            lambda _session, _repository, _repository_notebooks_names: (1, repository))
        output = e1.process_repository(safe_session, repository)

        assert output == "done"
        assert repository.notebooks_count is None
        assert repository.state == REP_N_ERROR

    def test_process_repository_no_status_extracted(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(state=REP_N_ERROR,
                                                            notebooks_count=1)

        monkeypatch.setattr(e1, 'find_notebooks', lambda _session, _repository: [])
        monkeypatch.setattr(e1, 'process_notebooks',
                            lambda _session, _repository, _repository_notebooks_names: (1, repository))
        monkeypatch.setattr(safe_session, 'commit', lambda: (None, 'error 1'))

        output = e1.process_repository(safe_session, repository, retry=True)
        repository = safe_session.query(Repository).first()
        assert "failed due 'error 1'" in output
        assert repository.state == REP_N_ERROR

    def test_process_repository_retry_success(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(state=REP_N_ERROR,
                                                            notebooks_count=1)

        monkeypatch.setattr(e1, 'find_notebooks', lambda _session, _repository: [])
        monkeypatch.setattr(e1, 'process_notebooks',
                            lambda _session, _repository, _repository_notebooks_names: (1, repository))
        output = e1.process_repository(safe_session, repository, retry=True)
        repository = safe_session.query(Repository).first()

        assert repository.state == REP_N_EXTRACTION
        captured = capsys.readouterr()
        assert "retrying to process" in captured.out
        assert output == "done"

    def test_process_repository_retry_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(state=REP_N_ERROR)

        monkeypatch.setattr(e1, 'find_notebooks', lambda _session, _repository: [])
        monkeypatch.setattr(e1, 'process_notebooks',
                            lambda _session, _repository, _repository_notebooks_names: (1, repository))
        output = e1.process_repository(safe_session, repository, retry=True)
        repository = safe_session.query(Repository).first()

        captured = capsys.readouterr()
        assert "retrying to process" in captured.out
        assert repository.notebooks_count is None
        assert output == "done"
        assert repository.state == REP_N_ERROR

    def test_process_repository_not_retry(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(state=REP_N_ERROR)

        output = e1.process_repository(safe_session, repository)

        assert output == "already processed"

    def test_process_repository_already_processed(self, session, monkeypatch):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(
            state=REP_N_EXTRACTION)

        output = e1.process_repository(safe_session, repository)

        assert output == "already processed"

    def test_process_repository_state_after(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(state=REP_P_EXTRACTION)

        output = e1.process_repository(safe_session, repository)

        assert output == "already processed"

    def test_process_repository_state_before(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session, interrupted=consts.N_STOPPED)
        repository = RepositoryFactory(safe_session).create(state=REP_FILTERED)

        output = e1.process_repository(safe_session, repository)

        assert "wrong script order" in output
