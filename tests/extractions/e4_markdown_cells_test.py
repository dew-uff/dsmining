import sys
import os


src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import src.consts as consts
import src.extractions.e4_markdown_cells as e4

from src.states import *
from nltk.corpus import stopwords
from src.db.database import CellMarkdownFeature
from src.extractions.e4_markdown_cells import process_markdown_cell
from tests.test_helpers.h1_stubs import stub_extract_features
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory, NotebookFactory, MarkdownCellFactory, CellMarkdownFeatureFactory


class TestE4MarkdownCellsProcessMarkdownCell:
    def test_process_markdown_cell_sucess(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   state=CELL_LOADED)

        monkeypatch.setattr(e4, 'extract_features', stub_extract_features)

        result = process_markdown_cell(session, repository.id, notebook.id, cell)
        session.commit()

        cell_markdown_features = session.query(CellMarkdownFeature).first()

        assert result == 'done'
        assert cell_markdown_features.cell_id == cell.id
        assert cell.state == CELL_PROCESSED

    def test_process_markdown_cell_already_processed(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   state=CELL_PROCESSED)
        result = process_markdown_cell(session, repository.id, notebook.id, cell)
        assert result == 'already processed'

    def test_process_markdown_cell_retry_error_not_exist_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   state=CELL_PROCESS_ERROR)
        monkeypatch.setattr(e4, 'extract_features', stub_extract_features)

        result = process_markdown_cell(session, repository.id, notebook.id, cell, True)
        session.commit()

        cell_markdown_features = session.query(CellMarkdownFeature).first()

        assert result == 'done'
        assert cell_markdown_features.cell_id == cell.id
        assert cell.state == CELL_PROCESSED

    def test_process_markdown_cell_retry_error_exists_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   state=CELL_PROCESS_ERROR)
        cell_markdown = CellMarkdownFeatureFactory(session).create(repository_id=repository.id,
                                                                   notebook_id=notebook.id,
                                                                   cell_id=cell.id)
        created_at = cell_markdown.created_at

        monkeypatch.setattr(e4, 'extract_features', stub_extract_features)

        result = process_markdown_cell(session, repository.id, notebook.id, cell, True)
        session.commit()

        cell_markdown_features = session.query(CellMarkdownFeature).first()

        assert result == 'done'
        assert cell_markdown_features.cell_id == cell.id
        assert cell.state == CELL_PROCESSED
        assert created_at != cell_markdown_features.created_at

    def test_process_markdown_cell_not_retry(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   state=CELL_PROCESS_ERROR)
        monkeypatch.setattr(e4, 'extract_features', stub_extract_features)

        result = process_markdown_cell(session, repository.id, notebook.id, cell)
        session.commit()


        assert result == 'already processed'
        assert cell.state == CELL_PROCESS_ERROR

    def test_process_markdown_cell_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   state=CELL_LOADED)

        def stub_extract_features_error(cell_source):  # noqa: F841
            raise Exception

        monkeypatch.setattr(e4, 'extract_features', stub_extract_features_error)

        result = process_markdown_cell(session, repository.id, notebook.id, cell)
        session.commit()

        cell_markdown_features = session.query(CellMarkdownFeature).first()

        assert 'Failed to process' in result
        assert cell.state == CELL_PROCESS_ERROR
        assert cell_markdown_features is None


class TestE4MarkdownCellsExtractFeatures:
    def test_process_markdown_extract_features(self, session):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   source='Este notebook tem o propósito de analisar\n'
                                                          'o nível de escolaridade brasileiro no ano de 2022\n\n')

        data = e4.extract_features(cell.source)

        assert data["language"] == "portuguese"
        assert data["lines"] == 4
        assert data["meaningful_lines"] == 2
        assert data["words"] == 16
        assert data['stopwords'] == 7  # este, o, de, o, de, no, de

    def test_process_markdown_extract_features_not_stopwords(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                   notebook_id=notebook.id,
                                                   source='Este notebook tem o propósito de analisar\n'
                                                          'o nível de escolaridade brasileiro no ano de 2022\n\n')

        def stub_stopwords_error(language):  # noqa: F841
            raise LookupError

        monkeypatch.setattr(stopwords, 'words', stub_stopwords_error)
        data = e4.extract_features(cell.source)

        assert data["language"] == "portuguese"
        assert data["lines"] == 4
        assert data["meaningful_lines"] == 2
        assert data["words"] == 16
        assert data['stopwords'] == 0
