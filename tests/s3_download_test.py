import shutil
import sys
import os

from src.config import TEST_REPOS_DIR

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import src.extractions.e1_notebooks_and_cells as e1

from IPython.core.inputtransformer2 import TransformerManager
from src.consts import C_OK, C_UNKNOWN_VERSION, C_SYNTAX_ERROR
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory
from tests.test_helpers.h1_stubs import get_notebook_nbrow, stub_KeyError, mock_load_rep_and_commits
from tests.test_helpers.h1_stubs import stub_IndentationError, get_notebook_node
from src.states import *
import src.s3_download as s3


class TestS3DownloadProcessRepository:
    def test_process_repository_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_FILTERED)

        monkeypatch.setattr(s3, 'load_repository_and_commits', mock_load_rep_and_commits)

        output = s3.process_repository(session=session, repository=repository)

        assert output == 'done'
        assert repository.state == REP_LOADED

    def test_process_repository_already_processed(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_LOADED)

        output = s3.process_repository(session=session, repository=repository)

        assert output == "already downloaded"

    def test_process_repository_state_after(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            state=REP_N_EXTRACTED)

        output = s3.process_repository(session=session, repository=repository)

        assert output == "already downloaded"

    def test_process_repository_retry_unavailable_success(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_UNAVAILABLE_FILES, commit="1")

        monkeypatch.setattr(s3, 'load_repository_and_commits', mock_load_rep_and_commits)
        os.makedirs(repository.path, exist_ok=True)
        output = s3.process_repository(session=session, repository=repository, retry=True)

        assert repository.state == REP_LOADED
        captured = capsys.readouterr()
        assert repository.path.exists() is False
        assert output == "done"
        assert "redownloading" in captured.out
        shutil.rmtree(TEST_REPOS_DIR, ignore_errors=True)

    def test_process_repository_retry_failed_to_clone(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_FAILED_TO_CLONE)

        monkeypatch.setattr(s3, 'load_repository_and_commits', mock_load_rep_and_commits)
        os.makedirs(repository.path, exist_ok=True)
        output = s3.process_repository(session=session, repository=repository, retry=True)

        assert repository.state == REP_LOADED
        captured = capsys.readouterr()
        assert "retrying to download" in captured.out
        assert output == "done"
        shutil.rmtree(TEST_REPOS_DIR, ignore_errors=True)


class TestS3DownloadLoadRepositoryAndCommits:
    def test_load_repository_commits(self, session):
        repository = RepositoryFactory(session).create(state=REP_FILTERED)

        s3.load_repository_and_commits(session, repository)

        commit = '8a34a4f653bdbdc01415a94dc20d4e9b97438965'



