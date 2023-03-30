""" Donwloads Repository from GitHub"""

import os
import sys
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path:
    sys.path.append(src)

import argparse
import src.consts as consts

from src.db.database import Commit, connect
from src.helpers.h1_git_helpers import git, extract_hash_parts, git_output, format_commit, remove_repo_and_prepare
from src.helpers.h3_utils import savepid, vprint, check_exit
from src.classes.c2_status_logger import StatusLogger
from src.classes.c1_safe_session import SafeSession
from src.helpers.h2_script_helpers import set_up_argument_parser
from src.helpers.h4_filters import filter_repositories

from src.config.states import REP_LOADED, REP_EMPTY, REP_STOPPED
from src.config.states import REP_FAILED_TO_CLONE, REP_UNAVAILABLE_FILES
from src.config.states import REP_ORDER, REP_ERRORS, states_after


def load_commits(full_dir):
    commits_info = []

    try:
        args = ["--git-dir", str(full_dir / ".git"), 'log',
                '--no-merges', '--pretty=format:%ci$_$%h$_$%an$_$%s']

        git_log_commits = git_output(*args).decode("utf-8")

        if git_log_commits:
            git_log_commits = git_log_commits.split("\n")
            git_log_commits = [x for x in git_log_commits if x != ""]

            for commit_ in git_log_commits:
                commit_row = format_commit(commit_, "commit")
                commits_info.append(commit_row)

        args = ["--git-dir", str(full_dir / ".git"),
                'log', '--merges', '--pretty=format:%ci$_$%h$_$%an$_$%s']
        git_log_merges = git_output(*args).decode("utf-8")

        if git_log_merges:
            git_log_merges = git_log_merges.split("\n")
            git_log_merges = [y for y in git_log_merges if y != ""]
            for merges_ in git_log_merges:
                merge_row = format_commit(merges_, "merge")
                commits_info.append(merge_row)

    except Exception as err:
        raise EnvironmentError("Load commits failed. Error:{}".format(err))

    return commits_info


def clone(part, end, repo, remote, branch=None, commit=None):
    """Clone git repository into a proper directory"""
    part_dir = consts.SELECTED_REPOS_DIR / "content" / part
    part_dir.mkdir(parents=True, exist_ok=True)
    full_dir = part_dir / end

    if full_dir.exists():
        vprint(1, "Repository already cloned."
                  "Delete it if you would like to re-run.")
        return full_dir, None, True
    else:
        args = ["clone"]
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
    remote = "https://github.com/{}.git".format(repo)

    if repository.commit and not retry:
        vprint(1, "Repository {} already loaded".format(repository))
        return

    try:
        vprint(1, "Remote: {}\nDownloading repository...".format(remote))

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
        vprint(0, 'Failed to download repository {} due to {}'
               .format(repository, err))
        repository.state = REP_FAILED_TO_CLONE
        session.add(repository)


def process_repository(session, repository, branch=None, commit=None, retry=False):
    """ Processes repository """

    if retry:
        if repository.state == REP_UNAVAILABLE_FILES:
            vprint(3, "redownloading {}".format(repository))
            commit = remove_repo_and_prepare(session, repository)
        elif retry and repository.state == REP_FAILED_TO_CLONE:
            vprint(3, "retrying to download {}".format(repository))
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

    query = filter_repositories(
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
        vprint(0, "Downloading repository {} from {}."
               .format(repository, repository.domain))

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
    consts.VERBOSE = args.verbose

    status = None

    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    with connect() as session, savepid():
        apply(
            session=SafeSession(session, interrupted=REP_STOPPED),
            status=status,
            selected_repositories=args.repositories,
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
