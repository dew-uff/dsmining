import sys
import os

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.extractions.e1_notebooks_and_cells as e1
from src.consts import N_OK, N_LOAD_ERROR, N_LOAD_FORMAT_ERROR, C_OK, C_UNKNOWN_VERSION, C_SYNTAX_ERROR, \
    N_LOAD_SYNTAX_ERROR
from tests.database_test import connection, session
from tests.factories.models_test import RepositoryFactory
from tests.test_helpers.h1_stubs import  get_notebook_nbrow
from tests.test_helpers.h1_stubs import stub_IndentationError, get_notebook_node
from tests.test_helpers.h1_stubs import stub_load_no_cells
from IPython.core.inputtransformer2 import TransformerManager
class TestE1NotebooksAndCellsLoadNotebooks:

    def test_load_notebooks(self, session):
        repository = RepositoryFactory(session).create()
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node()
        status = 0

        nbrow, cells_info, exec_count, status = e1.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) ==28
        assert status == 0

        markdown_cell = cells_info[0]
        assert markdown_cell["repository_id"] == repository.id
        assert markdown_cell["cell_type"] == 'markdown'
        assert markdown_cell["execution_count"] is None
        assert markdown_cell["processed"] == C_OK

        code_cell = cells_info[4]
        assert code_cell["repository_id"] == repository.id
        assert code_cell["cell_type"] == 'code'
        assert code_cell["execution_count"] == 2
        assert code_cell["processed"] == C_OK

    def test_load_notebooks_unknown_version(self, session):
        repository = RepositoryFactory(session).create()
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node()
        status = 0
        nbrow["language_version"] = 'unknown'

        nbrow, cells_info, exec_count, status = e1.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 28
        assert status == 0

        markdown_cell = cells_info[4]
        assert markdown_cell["repository_id"] == repository.id
        assert markdown_cell["cell_type"] == 'code'
        assert markdown_cell["execution_count"] == 2
        assert markdown_cell["processed"] == C_UNKNOWN_VERSION

    def test_load_notebooks_syntax_error(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create()
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0

        monkeypatch.setattr(TransformerManager, "transform_cell", stub_IndentationError)

        nbrow, cells_info, exec_count, status = e1.load_cells(repository.id, nbrow, notebook, status)
        captured = capsys.readouterr()
        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == N_LOAD_SYNTAX_ERROR
        assert cell["processed"] == C_SYNTAX_ERROR
        assert cell["source"] == ""
        assert "Error on cell transformation" in captured.out

    def test_load_notebooks_null_byte(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create()
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0
        notebook["cells"][0]["source"] = 'import matplotlib\0'

        nbrow, cells_info, exec_count, status = e1.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 1
        assert status == 0

        captured = capsys.readouterr()
        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == 0
        assert cell["processed"] == C_OK
        assert cell["source"] == 'import matplotlib\n\n'
        assert "Found null byte in source" in captured.out

    def test_load_notebooks_output(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create()
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0
        notebook["cells"][0]["source"] = 'import matplotlib\0'

        nbrow, cells_info, exec_count, status = e1.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 1
        assert status == 0

        captured = capsys.readouterr()
        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == 0
        assert cell["processed"] == C_OK
        assert cell["source"] == 'import matplotlib\n\n'
        assert "Found null byte in source" in captured.out