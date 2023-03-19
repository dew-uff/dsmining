import sys
import os
src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path: sys.path.append(src)

import src.consts as consts
import src.extractions.e5_code_cells as e5

from src.helpers.h1_utils import TimeoutError
from src.classes.c2_local_checkers import PathLocalChecker
from src.extractions.e5_code_cells import process_code_cell

from src.db.database import CellModule, CellDataIO
from tests.factories.models import RepositoryFactory
from tests.factories.models import NotebookFactory, CodeCellFactory
from tests.factories.models import CellModuleFactory, CellDataIOFactory
from tests.database_config import connection, session



class TestE5CodeCellsProcessCodeCell:
    def test_process_code_cell(self, session):
        module_name = 'pandas'
        caller, function_name, source  = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = CodeCellFactory(session).create(repository_id=repository.id,
                                               notebook_id=notebook.id,
                                               source=f"import {module_name} as pd\n"
                                                      f"df={caller}.{function_name}({source})")
        checker = PathLocalChecker("")
        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker)
        session.commit()
        module = session.query(CellModule).first()
        data_io = session.query(CellDataIO).first()

        assert result == 'done'
        assert cell.processed == consts.C_PROCESS_OK

        assert module.cell_id == cell.id
        assert module.module_name == module_name
        assert module.import_type == "import"

        assert data_io.cell_id == cell.id
        assert data_io.caller == caller
        assert data_io.function_name == function_name
        assert data_io.source == source


    def test_process_code_cell_already_processed(self, session):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = CodeCellFactory(session).create(repository_id=repository.id,
                                               notebook_id=notebook.id,
                                               processed=consts.C_PROCESS_OK)
        checker = PathLocalChecker("")
        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker)
        session.commit()

        assert result == 'already processed'
        assert cell.processed == consts.C_PROCESS_OK


    def test_process_code_cell_time_out(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = CodeCellFactory(session).create(repository_id=repository.id,
                                               notebook_id=notebook.id)
        checker = PathLocalChecker("")

        def mock_extract(_source, _checker):
            raise TimeoutError
        monkeypatch.setattr(e5, 'extract_features', mock_extract)

        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker)
        session.commit()

        assert result == 'Failed due to  Time Out Error.'
        assert cell.processed == consts.C_TIMEOUT


    def test_process_code_cell_syntax_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = CodeCellFactory(session).create(repository_id=repository.id,
                                               notebook_id=notebook.id)
        checker = PathLocalChecker("")

        def mock_extract(_source, _checker):
            raise SyntaxError
        monkeypatch.setattr(e5, 'extract_features', mock_extract)

        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker)
        session.commit()

        assert result == 'Failed due to Syntax Error.'
        assert cell.processed == consts.C_SYNTAX_ERROR


    def test_process_code_cell_other_errors(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = CodeCellFactory(session).create(repository_id=repository.id,
                                               notebook_id=notebook.id)
        checker = PathLocalChecker("")

        def mock_extract(_source, _checker):
            raise ValueError
        monkeypatch.setattr(e5, 'extract_features', mock_extract)

        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker)
        session.commit()

        assert 'Failed to process' in result
        assert cell.processed == consts.C_PROCESS_ERROR

    def test_process_code_cell_retry_process_error(self,session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = CodeCellFactory(session).create(repository_id=repository.id,
                                               notebook_id=notebook.id,
                                               processed=consts.C_PROCESS_ERROR,
                                               source=f"import {module_name} as pd\n"
                                                      f"df={caller}.{function_name}({source})")
        checker = PathLocalChecker("")

        cell_module = CellModuleFactory(session).create(cell_id=cell.id)
        cell_data_io = CellDataIOFactory(session).create(cell_id=cell.id)
        cm_created_at = cell_module.created_at
        cd_created_at = cell_data_io.created_at

        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker,
                                   skip_if_error=0)
        session.commit()
        module = session.query(CellModule).first()
        data_io = session.query(CellDataIO).first()

        assert result == 'done'
        assert cell.processed == consts.C_PROCESS_OK

        assert module.cell_id == cell.id
        assert cm_created_at != module.created_at

        assert data_io.cell_id == cell.id
        assert cd_created_at != data_io.created_at

    def test_process_code_cell_retry_process_syntax(self,session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = CodeCellFactory(session).create(repository_id=repository.id,
                                               notebook_id=notebook.id,
                                               processed=consts.C_SYNTAX_ERROR,
                                               source=f"import {module_name} as pd\n"
                                                      f"df={caller}.{function_name}({source})")
        checker = PathLocalChecker("")

        cell_module = CellModuleFactory(session).create(cell_id=cell.id)
        cell_data_io = CellDataIOFactory(session).create(cell_id=cell.id)
        cm_created_at = cell_module.created_at
        cd_created_at = cell_data_io.created_at

        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker,
                                   skip_if_syntaxerror=0)
        session.commit()
        module = session.query(CellModule).first()
        data_io = session.query(CellDataIO).first()

        assert result == 'done'
        assert cell.processed == consts.C_PROCESS_OK

        assert module.cell_id == cell.id
        assert cm_created_at != module.created_at

        assert data_io.cell_id == cell.id
        assert cd_created_at != data_io.created_at

    def test_process_code_cell_retry_process_timeout(self,session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = CodeCellFactory(session).create(repository_id=repository.id,
                                               notebook_id=notebook.id,
                                               processed=consts.C_TIMEOUT,
                                               source=f"import {module_name} as pd\n"
                                                      f"df={caller}.{function_name}({source})")
        checker = PathLocalChecker("")

        cell_module = CellModuleFactory(session).create(cell_id=cell.id)
        cell_data_io = CellDataIOFactory(session).create(cell_id=cell.id)
        cm_created_at = cell_module.created_at
        cd_created_at = cell_data_io.created_at

        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker,
                                   skip_if_timeout=0)
        session.commit()
        module = session.query(CellModule).first()
        data_io = session.query(CellDataIO).first()

        assert result == 'done'
        assert cell.processed == consts.C_PROCESS_OK

        assert module.cell_id == cell.id
        assert cm_created_at != module.created_at

        assert data_io.cell_id == cell.id
        assert cd_created_at != data_io.created_at