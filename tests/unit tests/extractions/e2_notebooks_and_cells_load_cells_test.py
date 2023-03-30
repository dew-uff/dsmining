import sys
import os
src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import src.extractions.e2_notebooks_and_cells as e2

from IPython.core.inputtransformer2 import TransformerManager
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory
from tests.stubs.others import stub_KeyError
from tests.stubs.notebook_dict import get_notebook_node, get_notebook_nbrow
from tests.stubs.nbf_read import stub_IndentationError
from src.states import *


class TestNotebooksAndCellsLoadCells:

    def test_load_cells(self, session):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node()
        status = 0

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 28
        assert status == 0

        assert nbrow["state"] == NB_LOADED

        markdown_cell = cells_info[0]
        assert markdown_cell["repository_id"] == repository.id
        assert markdown_cell["cell_type"] == 'markdown'
        assert markdown_cell["execution_count"] is None
        assert markdown_cell["state"] == CELL_LOADED

        code_cell = cells_info[4]
        assert code_cell["repository_id"] == repository.id
        assert code_cell["cell_type"] == 'code'
        assert code_cell["execution_count"] == 2
        assert code_cell["state"] == CELL_LOADED

    def test_load_cell_unknown_version(self, session):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node()
        status = 0
        nbrow["language_version"] = 'unknown'

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 28
        assert status == 0

        markdown_cell = cells_info[4]
        assert markdown_cell["repository_id"] == repository.id
        assert markdown_cell["cell_type"] == 'code'
        assert markdown_cell["execution_count"] == 2
        assert markdown_cell["state"] == CELL_UNKNOWN_VERSION

    def test_load_cell_syntax_error(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0

        monkeypatch.setattr(TransformerManager, "transform_cell", stub_IndentationError)

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        captured = capsys.readouterr()
        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == NB_LOAD_SYNTAX_ERROR
        assert cell["state"] == CELL_SYNTAX_ERROR
        assert cell["source"] == ""
        assert "Error on cell transformation" in captured.out

    def test_load_cell_null_byte(self, session, capsys):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0
        notebook["cells"][0]["source"] = 'import matplotlib\0'

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 1
        assert status == 0

        captured = capsys.readouterr()
        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == 0
        assert cell["state"] == CELL_LOADED
        assert cell["source"] == 'import matplotlib\n\n'
        assert "Found null byte in source" in captured.out

    def test_load_cell_output(self, session):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('display_data')
        status = 0
        notebook["cells"][0]["source"] = 'import matplotlib\0'

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 1
        assert status == 0
        assert nbrow["code_cells_with_output"] == 1

        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == 0
        assert cell["state"] == CELL_LOADED
        assert cell["output_formats"] == 'text/plain;image/png' or 'image/png;text/plain'

    def test_load_cell_raw_cell(self, session):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0
        notebook["cells"][0]["cell_type"] = 'raw'

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 1
        assert status == 0

        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == 0
        assert cell["state"] == CELL_LOADED
        assert nbrow["raw_cells"] == 1

    def test_load_cell_unknown(self, session):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0
        notebook["cells"][0]["cell_type"] = 'unknown'

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 1
        assert status == 0

        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == 0
        assert cell["state"] == CELL_LOADED
        assert nbrow["unknown_cell_formats"] == 1

    def test_load_cell_empty(self, session):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0
        notebook["cells"][0]["source"] = ''

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        assert len(cells_info) == 1
        assert status == 0

        cell = cells_info[0]

        assert len(cells_info) == 1
        assert status == 0
        assert cell["state"] == CELL_LOADED
        assert nbrow["empty_cells"] == 1

    def test_load_cell_key_error(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        name = "file.ipynb"
        nbrow = get_notebook_nbrow(repository.id, name)
        notebook = get_notebook_node('code_cell')
        status = 0

        monkeypatch.setattr(TransformerManager, "transform_cell", stub_KeyError)

        nbrow, cells_info, exec_count, status = e2.load_cells(repository.id, nbrow, notebook, status)
        captured = capsys.readouterr()

        assert status == NB_LOAD_FORMAT_ERROR
        assert "Error on cell extraction" in captured.out
