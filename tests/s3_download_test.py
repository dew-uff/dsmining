import shutil
import sys
import os

from src import config
from src.config import TEST_REPOS_DIR
from src.db.database import Commit
from src.helpers.h1_utils import SafeSession

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import src.extractions.e1_notebooks_and_cells as e1

from IPython.core.inputtransformer2 import TransformerManager
from src.consts import C_OK, C_UNKNOWN_VERSION, C_SYNTAX_ERROR
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory
from tests.test_helpers.h1_stubs import get_notebook_nbrow, stub_KeyError, mock_load_rep_and_commits, stub_repo_commits
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
    def test_load_repository_commits_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_FILTERED, commit=None)
        safe_session = SafeSession(session, interrupted=REP_STOPPED)
        commit_hash = b'8a34a4f653bdbdc01415a94dc20d4e9b97438965\n'

        def stub_clone(_part, _end, _repo, _remote, _branch, _commit):
            return repository.path, stub_repo_commits(), False

        monkeypatch.setattr(s3, 'clone', stub_clone)
        monkeypatch.setattr(s3, 'git_output', lambda *args, cwd: commit_hash)

        s3.load_repository_and_commits(safe_session, repository)
        safe_session.commit()
        commit = safe_session.query(Commit).first()

        assert safe_session.query(Commit).count() == 3
        assert repository.state == REP_LOADED
        assert commit.repository_id == repository.id

    def test_load_repository_no_commits(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_FILTERED, commit=None)
        safe_session = SafeSession(session, interrupted=REP_STOPPED)

        def stub_clone(_part, _end, _repo, _remote, _branch, _commit):
            return repository.path, None, False

        monkeypatch.setattr(s3, 'clone', stub_clone)
        monkeypatch.setattr(s3, 'git_output', lambda *args, cwd: b'')

        s3.load_repository_and_commits(safe_session, repository)
        safe_session.commit()

        assert safe_session.query(Commit).count() == 0
        assert repository.state == REP_EMPTY

    def test_load_repository_already_loaded(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        safe_session = SafeSession(session, interrupted=REP_STOPPED)

        s3.load_repository_and_commits(safe_session, repository)
        safe_session.commit()
        captured = capsys.readouterr()

        assert "already loaded" in captured.out
        assert safe_session.query(Commit).count() == 0
        assert repository.state == REP_LOADED

    def test_load_repository_commits_error(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_FILTERED, commit=None)
        safe_session = SafeSession(session, interrupted=REP_STOPPED)
        commit_hash = b'8a34a4f653bdbdc01415a94dc20d4e9b97438965\n'

        def stub_clone(_part, _end, _repo, _remote, _branch, _commit):
            raise EnvironmentError(f"Clone failed for {repository}")

        monkeypatch.setattr(s3, 'clone', stub_clone)
        monkeypatch.setattr(s3, 'git_output', lambda *args, cwd: commit_hash)

        s3.load_repository_and_commits(safe_session, repository)
        safe_session.commit()
        captured = capsys.readouterr()

        assert safe_session.query(Commit).count() == 0
        assert repository.state == REP_FAILED_TO_CLONE
        assert "Failed to download" in captured.out


class TestS3DownloadClone:
    def test_load_repository_commits_success(self, session, monkeypatch):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"

        def stub_load_commits(_full_dir):
            return stub_repo_commits()

        monkeypatch.setattr(s3, 'load_commits', stub_load_commits)

        full_dir, commits, already_exists = s3.clone(part, end, repo, remote,
                                                     branch=None, commit=None)

        assert already_exists is False
        assert full_dir == config.SELECTED_REPOS_DIR / "content" / part / end
        assert full_dir.exists() is True
        assert len(commits) == 3
        shutil.rmtree(str(full_dir), ignore_errors=True)
        assert full_dir.exists() is False

    def test_load_repository_commits_repo_exists(self, session, monkeypatch, capsys):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"

        def stub_load_commits(_full_dir):
            return stub_repo_commits()

        monkeypatch.setattr(s3, 'load_commits', stub_load_commits)

        full_dir, commits, already_exists = s3.clone(part, end, repo, remote, branch=None, commit=None)
        full_dir2, commits2, already_exists2 = s3.clone(part, end, repo, remote, branch=None, commit=None)
        captured = capsys.readouterr()

        assert already_exists is False
        assert already_exists2 is True

        assert full_dir == config.SELECTED_REPOS_DIR / "content" / part / end
        assert full_dir.exists() is True
        assert "Repository already cloned" in captured.out
        shutil.rmtree(str(full_dir), ignore_errors=True)
        assert full_dir.exists() is False
