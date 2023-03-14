import builtins
import shutil
import sys
import os
from unittest.mock import mock_open, patch

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)
import src.consts as consts
import src.extractions.e1_notebooks_and_cells as e1
from src.config import TEST_REPOS_DIR, LOGS_DIR
from src.helpers.h1_utils import SafeSession
from src.db.database import Repository, Notebook, Cell
import nbformat as nbf


from tests.database_test import connection, session
from tests.factories.models_test import RepositoryFactory, NotebookFactory
from tests.test_helpers.h1_stubs import stub_nbf_read, get_empty_nbrow, stub_load_cells


class TestE1NotebooksAndCellsLoadNotebook:

    def test_load_notebooks(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        name = "file.ipynb"
        nbrow = get_empty_nbrow(repository, name)

        monkeypatch.setattr('builtins.open', mock_open())
        monkeypatch.setattr(nbf, 'read', stub_nbf_read)
        monkeypatch.setattr(e1, 'load_cells', stub_load_cells)


        nbrow, cells_info = e1.load_notebook(repository.id, repository.path, name, nbrow)
        assert len(cells_info) == 28
        assert nbrow["language"] == 'python'
        assert nbrow["processed"] == consts.N_OK


