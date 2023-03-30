import os
import sys
src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import nbformat as nbf
import src.extractions.e2_notebooks_and_cells as e2

from src.states import REP_LOADED, NB_LOADED, NB_LOAD_ERROR, NB_LOAD_FORMAT_ERROR

from unittest.mock import mock_open
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory
from tests.stubs.notebook_dict import get_empty_nbrow
from tests.stubs.nbf_read import stub_nbf_read, stub_nbf_readOSError, stub_nbf_readException
from tests.stubs.load_cells import stub_load_cells, stub_load_no_cells


class TestNotebooksAndCellsLoadNotebooks:

    def test_load_notebooks(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_empty_nbrow(repository, name)

        monkeypatch.setattr('builtins.open', mock_open())
        monkeypatch.setattr(nbf, 'read', stub_nbf_read)
        monkeypatch.setattr(e2, 'load_cells', stub_load_cells)

        nbrow, cells_info = e2.load_notebook(repository.id, repository.path, name, nbrow)
        assert len(cells_info) == 28
        assert nbrow["language"] == 'python'
        assert nbrow["state"] == NB_LOADED

    def test_load_notebooksOSError(self, session, monkeypatch, capsys):

        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_empty_nbrow(repository, name)

        monkeypatch.setattr('builtins.open', mock_open())
        monkeypatch.setattr(nbf, 'read', stub_nbf_readOSError)

        nbrow, cells_info = e2.load_notebook(repository.id, repository.path, name, nbrow)

        ''' capsys does not receive ouput if timeout is enabled
        and an Exception is thrown comment timeout 
        if you want to test output '''

        # captured = capsys.readouterr()
        # assert "Failed to open notebook" in captured.out

        assert len(cells_info) == 0
        assert nbrow["state"] == NB_LOAD_ERROR

    def test_load_notebooksOSErrorLink(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_empty_nbrow(repository, name)

        monkeypatch.setattr('builtins.open', mock_open())
        monkeypatch.setattr(nbf, 'read', stub_nbf_readOSError)
        monkeypatch.setattr('os.path.islink', lambda path: True)

        nbrow, cells_info = e2.load_notebook(repository.id, repository.path, name, nbrow)

        assert len(cells_info) == 0
        assert nbrow["state"] == NB_LOAD_ERROR

        ''' capsys does not receive ouput if timeout is enabled
        and an Exception is thrown comment timeout
        if you want to test output '''

        # captured = capsys.readouterr()
        # assert "Failed to open notebook" in captured.out
        # assert "Notebook is broken link" in captured.out

    def test_load_notebooksException(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_empty_nbrow(repository, name)

        monkeypatch.setattr('builtins.open', mock_open())
        monkeypatch.setattr(nbf, 'read', stub_nbf_readException)

        nbrow, cells_info = e2.load_notebook(repository.id, repository.path, name, nbrow)

        assert len(cells_info) == 0
        assert nbrow["state"] == NB_LOAD_FORMAT_ERROR

        ''' capsys does not receive ouput if timeout is enabled
                and an Exception is thrown comment timeout 
                if you want to test output '''
        # captured = capsys.readouterr()
        # assert "Failed to load notebook" in captured.out

    def test_load_notebooksNoCells(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_empty_nbrow(repository, name)

        monkeypatch.setattr('builtins.open', mock_open())
        monkeypatch.setattr(nbf, 'read', stub_nbf_read)
        monkeypatch.setattr(e2, 'load_cells', stub_load_no_cells)

        nbrow, cells_info = e2.load_notebook(repository.id, repository.path, name, nbrow)

        assert len(cells_info) == 0
        assert nbrow["state"] == NB_LOAD_FORMAT_ERROR
