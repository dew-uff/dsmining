""" Donwloads Repository from GitHub"""

import os
import sys

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path:
    sys.path.append(src)

import argparse
import subprocess
import shutil
import src.config as config

from src.states import *
from src.db.database import Commit, connect
from src.helpers.git_helpers import git, extract_hash_parts, git_output, format_commit, remove_repo_and_prepare
from src.helpers.h1_utils import savepid, vprint, StatusLogger, SafeSession, check_exit
from src.helpers.h3_script_helpers import set_up_argument_parser, filter_repositories


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

    if full_dir.exists():
        vprint(1, f"Repository already cloned."
                  f"Delete it if you would like to re-run.")
        return full_dir, None, True
    else:
        args = ["clone"]
        args += [remote, str(full_dir)]

        if branch is not None:
            args.append("-b")
            args.append(branch)

        if git(*args) != 0:
            raise EnvironmentError(f"Clone failed for {repo}")

        if commit is not None:

            args = [
                "--git-dir", str(full_dir / ".git"),
                "--work-tree", str(full_dir),
                "checkout",
                commit
            ]

            if git(*args) != 0:
                raise EnvironmentError(
                    "Checkout failed for {}/{}".format(repo, commit)
                )

        commits = load_commits(full_dir)
        return full_dir, commits, False


def load_repository_and_commits(session, repository,  commit=None, branch=None, retry=False):
    """ Clones repository and extracts its information"""

    repo = repository.repository
    part, end = extract_hash_parts(repo)
    remote = f"https://github.com/{repo}.git"

    if repository.commit and not retry:
        vprint(1, f"Repository {repository} already loaded")
        return

    try:
        vprint(1, f"Remote: {remote}\nDownloading repository...")

        full_dir, repo_commits, already_exists = clone(part, end, repo, remote, branch, commit)

        commit = git_output("rev-parse", "HEAD", cwd=str(full_dir)).decode("utf-8").strip()

        repository.hash_dir1 = part
        repository.hash_dir2 = end
        repository.commit = commit
        repository.state = REP_LOADED

        if already_exists:
            session.add(repository)
        elif repo_commits:
            session.dependent_add(
                repository, [Commit(**commitrow) for commitrow in repo_commits], "repository_id"
            )
        else:
            repository.state = REP_EMPTY
            session.add(repository)
    except Exception as err:
        vprint(0, f'Failed to download repository {repository} due to {err}')
        repository.state = REP_FAILED_TO_CLONE
        session.add(repository)


def process_repository(session, repository, branch=None, commit=None, retry=False):
    """ Processes repository """

    if retry:
        if repository.state == REP_UNAVAILABLE_FILES:
            vprint(3, f"redownloading {repository}")
            commit = remove_repo_and_prepare(session, repository)
        elif retry and repository.state == REP_FAILED_TO_CLONE:
            vprint(3, f"retrying to download {repository}")
            commit = remove_repo_and_prepare(session, repository)

    if repository.state == REP_LOADED \
            or repository.state in REP_ERRORS\
            or repository.state in states_after(REP_LOADED, REP_ORDER):
        return "already downloaded"

    load_repository_and_commits(
        session, repository, commit=commit, branch=branch, retry=retry
    )

    session.commit()
    return "done"


def apply(session, status, selected_repositories, retry, count,
          interval, reverse, check, branch, commit):
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
                retry=retry
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
            commit=args.commit
        )


if __name__ == "__main__":
    main()
