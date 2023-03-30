import shutil
import sys
import os

import pytest

from src import config
from src.config import TEST_REPOS_DIR
from src.db.database import Commit
from src.classes.c1_safe_session import SafeSession

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory
from tests.stubs.commits import stub_repo_commits, mock_load_rep_and_commits
from src.states import *
import src.extractions.e1_download as e1


class TestDownloadProcessRepository:
    def test_process_repository_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_FILTERED)

        monkeypatch.setattr(e1, 'load_repository_and_commits', mock_load_rep_and_commits)

        output = e1.process_repository(session=session, repository=repository)

        assert output == 'done'
        assert repository.state == REP_LOADED

    def test_process_repository_already_processed(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_LOADED)

        output = e1.process_repository(session=session, repository=repository)

        assert output == "already downloaded"

    def test_process_repository_state_after(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(
            state=REP_N_EXTRACTED)

        output = e1.process_repository(session=session, repository=repository)

        assert output == "already downloaded"

    def test_process_repository_retry_unavailable_success(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_UNAVAILABLE_FILES, commit="1")

        monkeypatch.setattr(e1, 'load_repository_and_commits', mock_load_rep_and_commits)
        os.makedirs(repository.path, exist_ok=True)
        output = e1.process_repository(session=session, repository=repository, retry=True)

        assert repository.state == REP_LOADED
        captured = capsys.readouterr()
        assert repository.path.exists() is False
        assert output == "done"
        assert "redownloading" in captured.out
        shutil.rmtree(TEST_REPOS_DIR, ignore_errors=True)

    def test_process_repository_retry_failed_to_clone(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_FAILED_TO_CLONE)

        monkeypatch.setattr(e1, 'load_repository_and_commits', mock_load_rep_and_commits)
        os.makedirs(repository.path, exist_ok=True)
        output = e1.process_repository(session=session, repository=repository, retry=True)

        assert repository.state == REP_LOADED
        captured = capsys.readouterr()
        assert "retrying to download" in captured.out
        assert output == "done"
        shutil.rmtree(TEST_REPOS_DIR, ignore_errors=True)


class TestDownloadLoadRepositoryAndCommits:
    def test_load_repository_commits_success(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_FILTERED, commit=None)
        safe_session = SafeSession(session, interrupted=REP_STOPPED)
        commit_hash = b'8a34a4f653bdbdc01415a94dc20d4e9b97438965\n'

        def stub_clone(_part, _end, _repo, _remote, _branch, _commit):
            return repository.path, stub_repo_commits(), False

        monkeypatch.setattr(e1, 'clone', stub_clone)
        monkeypatch.setattr(e1, 'git_output', lambda *args, cwd: commit_hash)

        e1.load_repository_and_commits(safe_session, repository)
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
        monkeypatch.setattr(e1, 'clone', stub_clone)
        monkeypatch.setattr(e1, 'git_output', lambda *args, cwd: b'')

        e1.load_repository_and_commits(safe_session, repository)
        safe_session.commit()

        assert safe_session.query(Commit).count() == 0
        assert repository.state == REP_EMPTY

    def test_load_repository_path_already_exists(self, session, monkeypatch):
        repository = RepositoryFactory(session).create(state=REP_FILTERED, commit=None)
        safe_session = SafeSession(session, interrupted=REP_STOPPED)

        def stub_clone(_part, _end, _repo, _remote, _branch, _commit):
            return repository.path, None, True

        monkeypatch.setattr(e1, 'clone', stub_clone)
        monkeypatch.setattr(e1, 'git_output', lambda *args, cwd: b'')

        e1.load_repository_and_commits(safe_session, repository)
        safe_session.commit()

        assert safe_session.query(Commit).count() == 0
        assert repository.state == REP_LOADED

    def test_load_repository_already_loaded(self, session, monkeypatch, capsys):
        repository = RepositoryFactory(session).create(state=REP_LOADED)
        safe_session = SafeSession(session, interrupted=REP_STOPPED)

        e1.load_repository_and_commits(safe_session, repository)
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

        monkeypatch.setattr(e1, 'clone', stub_clone)

        e1.load_repository_and_commits(safe_session, repository)
        safe_session.commit()
        captured = capsys.readouterr()

        assert safe_session.query(Commit).count() == 0
        assert repository.state == REP_FAILED_TO_CLONE
        assert "Failed to download" in captured.out


class TestDownloadClone:
    def test_load_repository_commits_success(self, session, monkeypatch):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"

        def stub_load_commits(_full_dir):
            return stub_repo_commits()

        monkeypatch.setattr(e1, 'load_commits', stub_load_commits)

        full_dir, commits, already_exists = e1.clone(part, end, repo, remote,
                                                     branch=None, commit=None)

        assert already_exists is False
        assert full_dir == config.SELECTED_REPOS_DIR / "content" / part / end
        assert full_dir.exists() is True
        assert len(commits) == 3
        shutil.rmtree(config.TEST_REPOS_DIR, ignore_errors=True)
        assert full_dir.exists() is False

    def test_load_repository_commits_repo_exists(self, session, monkeypatch, capsys):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"

        def stub_load_commits(_full_dir):
            return stub_repo_commits()

        monkeypatch.setattr(e1, 'load_commits', stub_load_commits)

        full_dir, commits, already_exists = e1.clone(part, end, repo, remote, branch=None, commit=None)
        full_dir2, commits2, already_exists2 = e1.clone(part, end, repo, remote, branch=None, commit=None)
        captured = capsys.readouterr()

        assert already_exists is False
        assert already_exists2 is True

        assert full_dir == config.SELECTED_REPOS_DIR / "content" / part / end
        assert full_dir.exists() is True
        assert "Repository already cloned" in captured.out
        shutil.rmtree(config.TEST_REPOS_DIR, ignore_errors=True)
        assert full_dir.exists() is False

    def test_load_repository_commits_with_commit(self, session, monkeypatch):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"
        commit = "ab142cf"

        full_dir, commits, already_exists = e1.clone(part, end, repo, remote,
                                                     branch=None, commit=commit)
        last_commit = commits[5]

        assert already_exists is False
        assert full_dir == config.SELECTED_REPOS_DIR / "content" / part / end
        assert full_dir.exists() is True
        assert len(commits) == 6
        assert last_commit["hash"] == commit
        shutil.rmtree(config.TEST_REPOS_DIR, ignore_errors=True)
        assert full_dir.exists() is False

    def test_load_repository_commits_with_branch(self, session, monkeypatch):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"
        branch = "test"

        full_dir, commits, already_exists = e1.clone(part, end, repo, remote,
                                                     branch=branch, commit=None)

        assert already_exists is False
        assert full_dir == config.SELECTED_REPOS_DIR / "content" / part / end
        assert full_dir.exists() is True
        assert len(commits) > 15
        shutil.rmtree(config.TEST_REPOS_DIR, ignore_errors=True)
        assert full_dir.exists() is False

    def test_load_repository_commits_clone_error(self, session, monkeypatch):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"

        def stub_git(*args):
            if "clone" in args:
                return -1
            else:
                return 0

        monkeypatch.setattr(e1, 'git', stub_git)
        with pytest.raises(EnvironmentError):
            e1.clone(part, end, repo, remote, branch=None, commit=None)

    def test_load_repository_commits_checkout_error(self, session, monkeypatch):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"
        commit = "ab142cf"

        def stub_git(*args):
            if "checkout" in args:
                return -1
            else:
                return 0
        monkeypatch.setattr(e1, 'git', stub_git)
        with pytest.raises(EnvironmentError):
            e1.clone(part, end, repo, remote, branch=None, commit=commit)

        shutil.rmtree(config.TEST_REPOS_DIR, ignore_errors=True)


class TestDownloadLoadCommits:
    def test_load_commits(self, session, monkeypatch):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"

        commit = b'2022-12-20 09:01:24 -0300$_$d504211$_$luamz$_$Fixing path problems in linux\n'
        merge = b"2022-12-20 09:01:43 -0300$_$f55de22$_$luamz$_$Merge branch 'master'\n"

        def stub_git(*args):
            if "--no-merges" in args:
                return commit
            elif "--merges" in args:
                return merge
        monkeypatch.setattr(e1, 'git_output', stub_git)

        full_dir, commits, already_exists = e1.clone(part, end, repo, remote,
                                                     branch=None, commit=None)

        assert full_dir.exists() is True
        assert len(commits) == 2
        assert commits[0]["type"] == "commit"
        assert commits[1]["type"] == "merge"

        shutil.rmtree(config.TEST_REPOS_DIR, ignore_errors=True)
        assert full_dir.exists() is False

    def test_load_commits_invalid_commit(self, session, monkeypatch):
        part = "test"
        end = "test1"
        remote = "https://github.com/luamz/save-marine"
        repo = "luamz/save-marine"

        invalid_commit = b'2022-12-20 09:01:24 -0300$_$d504211$_$luamz\n'

        def stub_git(*args):
            if "--no-merges" in args:
                return invalid_commit
        monkeypatch.setattr(e1, 'git_output', stub_git)

        with pytest.raises(EnvironmentError):
            e1.clone(part, end, repo, remote, branch=None, commit=None)

        shutil.rmtree(config.TEST_REPOS_DIR, ignore_errors=True)

