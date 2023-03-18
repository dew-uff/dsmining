import sys
import os

from unittest.mock import mock_open

import chardet

from src.classes.c2_local_checkers import PathLocalChecker
from src.extractions.e5_code_cells import process_code_cell
from tests.factories.models import PythonFileFactory, RequirementFileFactory, NotebookFactory, CodeCellFactory
from tests.test_helpers.h1_stubs import stub_unzip, stub_unzip_failed, REQUIREMENTS_TXT

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.consts as consts
import src.extractions.e3_requirement_files as e3
from src.db.database import Repository, PythonFile, RequirementFile, CellModule, CellDataIO
from src.config import Path
from tests.database_config import connection, session
from tests.factories.models import RepositoryFactory


class TestE5CodeCellsExtract:
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
                                               notebook_id=notebook.id,
                                               processed=consts.C_PROCESS_OK)
        checker = PathLocalChecker("")
        result = process_code_cell(session=session, repository_id=repository.id,
                                   notebook_id=notebook.id, cell=cell, checker=checker)
        session.commit()

        assert result == 'already processed'
        assert cell.processed == consts.C_PROCESS_OK