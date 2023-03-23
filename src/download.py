""" Load Repository from GitHub"""

import os
import sys

from src.helpers.h3_script_helpers import set_up_argument_parser, filter_repositories

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path:
    sys.path.append(src)

import pytz
import argparse
import hashlib
import subprocess
import shutil
import src.consts as consts
import src.config as config

from datetime import datetime
from future.moves.urllib.parse import urlparse
from src.db.database import Repository, Commit, connect
from src.helpers.h1_utils import mount_basedir, savepid, vprint, StatusLogger, SafeSession, check_exit
from src.states import *


def git(*args):
    """Invoke git"""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.check_call(["git"] + list(args), env=env)


def git_output(*args, cwd=None):
    """Invoke git command and return output"""
    return subprocess.check_output(["git"] + list(args), cwd=cwd)


def format_commit(line, commit_type):
    commit_datetime, commit_hash, author, message = line.split(',', 3)
    commit_datetime = datetime.strptime(commit_datetime, "%Y-%m-%d %H:%M:%S %z")
    commit_datetime = commit_datetime.astimezone(pytz.timezone('GMT'))
    commit_row = {
        "repository_id": None,
        "type": commit_type,
        "hash": commit_hash,
        "date": commit_datetime,
        "author": author,
        "message": message
    }
    return commit_row


def load_commits(full_dir):
    git_log_commits = subprocess.check_output(
        ['git', "--git-dir", str(full_dir / ".git"),
         'log', '--no-merges', '--pretty=format:%ci,%h,%an,%s'], stderr=subprocess.STDOUT
    ).decode("utf-8")

    commits_info = []

    if git_log_commits:
        git_log_commits = git_log_commits.split("\n")
        for cc in git_log_commits:
            commit_row = format_commit(cc, "commit")
            commits_info.append(commit_row)

    git_log_merges = subprocess.check_output(
        ['git', "--git-dir", str(full_dir / ".git"),
         'log', '--merges', '--pretty=format:%ci,%h,%an,%s'], stderr=subprocess.STDOUT
    ).decode("utf-8")

    if git_log_merges:
        git_log_merges = git_log_merges.split("\n")
        for cm in git_log_merges:
            commit_row = format_commit(cm, "merge")
            commits_info.append(commit_row)

    return commits_info


def clone(part, end, repo, remote, branch=None, commit=None):
    """Clone git repository into a proper directory"""
    part_dir = config.SELECTED_REPOS_DIR / "content" / part
    part_dir.mkdir(parents=True, exist_ok=True)
    full_dir = part_dir / end

    if (
            full_dir.exists() and
            (
                    not (full_dir / ".git").exists()
                    or list(full_dir.iterdir()) == [full_dir / ".git"]
            )
    ):
        shutil.rmtree(str(full_dir), ignore_errors=True)

    if not full_dir.exists():
        args = ["clone"]

        if commit is None:
            args += ["--depth", "1"]
        args += [remote, str(full_dir)]

        if branch is not None:
            args.append("-b")
            args.append(branch)

        if git(*args) != 0:
            raise EnvironmentError("Clone failed for {}".format(repo))

        if commit is not None:

            args = [
                "--git-dir", str(full_dir / ".git"),
                "--work-tree", str(full_dir),
                "checkout"
            ]

            if git(*args) != 0:
                raise EnvironmentError("Checkout failed for {}/{}".format(
                    repo, commit
                ))

            commits = load_commits(full_dir)

            return full_dir, commits

    return full_dir, None


def extract_hash_parts(repo):
    """Extract hash parts from repo"""
    full_hash = hashlib.sha1(repo.encode("utf-8")).hexdigest()
    return full_hash[:2], full_hash[2:]


def load_repository_and_commits(session, repository,
                                branch=None, commit=None, clone_existing=False):
    """ Clones repository and extracts its information"""
    if clone_existing:
        shutil.rmtree(str(repository.path / ".git"), ignore_errors=True)

        deleted = session.query(Commit).filter(
            Commit.repository_id == repository.id
        ).delete()

        if deleted:
            vprint(2, f"Deleted commits from {repository} ")

        repository.state = REP_FILTERED

    repo = repository.repository
    part, end = extract_hash_parts(repo)
    remote = f"https://github.com/{repo}.git"

    vprint(1, f"Remote: {remote}")
    full_dir, all_commits = clone(part, end, repo, remote, branch, commit)

    commit = git_output("rev-parse", "HEAD", cwd=str(full_dir)).decode("utf-8").strip()

    vprint(1, "Finding files")

    repository.hash_dir1 = part
    repository.hash_dir2 = end
    repository.commit = commit

    if all_commits:
        session.dependent_add(
            repository, [Commit(**commitrow) for commitrow in all_commits], "repository_id"
        )
    else:
        session.add(repository)


def process_repository(session, repository, branch, commit,
                       retry=False, clone_existing=False):
    """ Processes repository """

    if retry and repository.state == REP_UNAVAILABLE_FILES:
        session.add(repository)
        vprint(3, "retrying to download{}".format(repository))
        repository.state = REP_FILTERED
    elif repository.state == REP_LOADED \
            or repository.state in REP_ERRORS\
            or repository.state in states_after(REP_LOADED, REP_ORDER):
        return "already processed"

    load_repository_and_commits(
        session, repository=repository, branch=branch,
        commit=commit, clone_existing=clone_existing
    )

    session.add(repository)
    session.commit()
    return "done"


def apply(session, status, selected_repositories, retry, count,
          interval, reverse, check, branch, commit, clone_existing=False):
    while selected_repositories:

        selected_repositories, query = filter_repositories(
            session=session,
            selected_repositories=selected_repositories,
            count=count,
            interval=interval, reverse=reverse
        )

        for repository in query:

            if check_exit(check):
                vprint(0, "Found .exit file. Exiting")
                return

            status.report()
            vprint(0, f"Downloading repository {repository} from {repository.domain}.")

            result = process_repository(
                session=session,
                repository=repository,
                branch=branch,
                commit=commit,
                retry=retry,
                clone_existing=clone_existing
            )

            vprint(0, result)

            status.count += 1
            session.commit()


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]

    parser = argparse.ArgumentParser(description="Download Repository via URL")
    parser = set_up_argument_parser(parser, script_name)
    parser.add_argument("-br", "--branch", type=str,
                        help="specific branch")
    parser.add_argument("-ct", "--commit", type=str,
                        help="specific commit")
    parser.add_argument("-ce", "--clone-existing", action='store_true',
                        help="clone even if repository exists")

    args = parser.parse_args()
    config.VERBOSE = args.verbose

    status = None

    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    with connect() as session, savepid():
        apply(
            session=SafeSession(session, interrupted=REP_STOPPED),
            status=status,
            selected_repositories=args.repositories or True,
            retry=True if args.retry_errors else False,
            count=args.count,
            interval=args.interval,
            reverse=args.reverse,
            check=set(args.check),
            branch=args.branch,
            commit=args.commit,
            clone_existing=True if args.clone_existing else False
        )


if __name__ == "__main__":
    main()
