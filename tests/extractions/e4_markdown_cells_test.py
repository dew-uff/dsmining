import sys
import os

from tests.test_helpers.h1_stubs import stub_extract_features

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)







import chardet
import src.consts as consts
from src.config import Path
from unittest.mock import mock_open
from src.db.database import Repository, PythonFile, RequirementFile, CellMarkdownFeature

import src.extractions.e4_markdown_cells as e4
from src.extractions.e4_markdown_cells import process_markdown_cell

from tests.database_config import connection, session
from tests.factories.models import RepositoryFactory, NotebookFactory, MarkdownCellFactory, CellMarkdownFeatureFactory


class TestE4MarkdownCells:
    def test_process_markdown_cell_sucess(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id = repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id)

        monkeypatch.setattr(e4, 'extract_features', stub_extract_features)

        result = process_markdown_cell(
            session, repository.id, notebook.id, cell, consts.C_PROCESS_ERROR
        )
        session.commit()

        cell_markdown_features = session.query(CellMarkdownFeature).first()

        assert result == 'done'
        assert cell_markdown_features.cell_id == cell.id
        assert cell.processed == consts.C_PROCESS_OK


    def test_process_markdown_cell_already_processed(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id = repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   processed=consts.C_PROCESS_OK)
        result = process_markdown_cell(
            session, repository.id, notebook.id, cell, consts.C_PROCESS_ERROR
        )
        assert result == 'already processed'


    def test_process_markdown_cell_retry_error_not_exist_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   processed=consts.C_PROCESS_ERROR)
        monkeypatch.setattr(e4, 'extract_features', stub_extract_features)

        result = process_markdown_cell(
            session, repository.id, notebook.id, cell, 0
        )
        session.commit()

        cell_markdown_features = session.query(CellMarkdownFeature).first()

        assert result == 'done'
        assert cell_markdown_features.cell_id == cell.id
        assert cell.processed == consts.C_PROCESS_OK

    def test_process_markdown_cell_retry_error_exists_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   processed=consts.C_PROCESS_ERROR)
        cell_markdown = CellMarkdownFeatureFactory(session).create(repository_id=repository.id,
                                                                   notebook_id=notebook.id,
                                                                   cell_id=cell.id)
        created_at = cell_markdown.created_at

        monkeypatch.setattr(e4, 'extract_features', stub_extract_features)

        result = process_markdown_cell(
            session, repository.id, notebook.id, cell, 0
        )
        session.commit()

        cell_markdown_features = session.query(CellMarkdownFeature).first()

        assert result == 'done'
        assert cell_markdown_features.cell_id == cell.id
        assert cell.processed == consts.C_PROCESS_OK
        assert created_at != cell_markdown_features.created_at


    def test_process_markdown_cell_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id = repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id)

        def stub_extract_features_error(cell_source):
            raise Exception
        monkeypatch.setattr(e4, 'extract_features', stub_extract_features_error)

        result = process_markdown_cell(
            session, repository.id, notebook.id, cell, consts.C_PROCESS_ERROR
        )
        session.commit()

        cell_markdown_features = session.query(CellMarkdownFeature).first()

        assert  'Failed to process' in result
        assert cell.processed == consts.C_PROCESS_ERROR
        assert cell_markdown_features is None

