""" Extracts python files from repositories"""

import os
import argparse
import src.config as config
import src.consts as consts

from src.db.database import PythonFile, connect
from src.helpers.h1_utils import vprint, StatusLogger, check_exit, savepid, find_files, mount_basedir
from src.helpers.h3_script_helpers import filter_repositories
from src.helpers.h4_unzip_repositories import unzip_repository


def find_python_files(session, repository):
    """ Finds all python files in a repository but setup.py """
    python_files = []

    if not repository.path.exists():
        msg = unzip_repository(session, repository)
        if msg != "done":
            vprint(2, "repository not found")
            repository.processed |= consts.R_UNAVAILABLE_FILES
            session.add(repository)
            session.commit()
            return python_files

    files = find_files(repository.path, "*.py")
    for file in files:
        if "/setup.py" not in str(file) and str(file) != 'setup.py':
            python_files.append(str(file.relative_to(repository.path)))

    return python_files


def process_python_files(session, repository, python_files_names, count):
    no_errors = True

    if not repository.path.exists():
        vprint(2, "Unzipping repository: {}".format(repository.zip_path))
        msg = unzip_repository(session, repository)
        if msg != "done":
            vprint(2, msg)
            no_errors = False
            return count, no_errors

    for name in python_files_names:
        if not name:
            continue

        count += 1

        python_file = session.query(PythonFile).filter(
            PythonFile.repository_id == repository.id,
            PythonFile.name == name,
        ).first()

        if python_file is not None:
            if python_file.processed & consts.PF_ERROR:
                session.delete(python_file)
                session.commit()

        try:
            vprint(3, "Loading python file {}".format(name))

            file_path = str(repository.path) + os.sep + name

            with open(file_path) as f:
                source = f.read()

            with open(file_path) as f:
                total = len(f.readlines())

            if total == 0:
                pf_processed = consts.PF_EMPTY
            else:
                pf_processed = consts.PF_OK

            python_file = PythonFile(
                repository_id=repository.id,
                name=name,
                source=source,
                total_lines=total,
                processed=pf_processed
            )

            session.add(python_file)
        except Exception as err:

            vprint(1, "Failed to load python file {} due {!r}".format(name, err))

            # We mark this python file as broken and keep adding the rest.
            python_file = PythonFile(
                repository_id=repository.id,
                name=name,
                processed=consts.PF_ERROR
            )
            session.add(python_file)

    return count, no_errors


def process_repository(session, repository, skip_if_error=consts.R_P_ERROR):
    """ Processes repository """
    if repository.processed & (consts.R_P_EXTRACTION + skip_if_error):
        return "already processed"

    if repository.processed & consts.R_P_ERROR:
        session.add(repository)
        vprint(3, "retrying to process {}".format(repository))
        repository.processed -= consts.R_P_ERROR

    count = 0
    repository_python_files_names = find_python_files(session, repository)

    count, no_errors = process_python_files(session, repository, repository_python_files_names, count)
    if no_errors:
        repository.processed |= consts.R_P_EXTRACTION
        repository.python_files_count = count
    else:
        repository.processed |= consts.R_P_ERROR

    session.add(repository)
    session.commit()
    return "done"


def apply(
        session, status, selected_repositories, skip_if_error,
        count, interval, reverse, check
):
    while selected_repositories:
        selected_repositories, query = filter_repositories(
            session=session,
            selected_repositories=selected_repositories,
            skip_if_error=skip_if_error, count=count,
            interval=interval, reverse=reverse,
            skip_already_processed=consts.R_P_EXTRACTION)

        for repository in query:
            if check_exit(check):
                vprint(0, "Found .exit file. Exiting")
                return
            status.report()
            vprint(0, "Extracting python files from {}".format(repository))
            with mount_basedir():
                result = process_repository(
                    session,
                    repository,
                    skip_if_error
                )
                vprint(1, result)
            status.count += 1
            session.commit()


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(
        description="Extract requirement files from registered repositories")
    parser.add_argument("-v", "--verbose", type=int, default=config.VERBOSE,
                        help="increase output verbosity")
    parser.add_argument("-n", "--repositories", type=int, default=None,
                        nargs="*",
                        help="repositories ids")
    parser.add_argument("-i", "--interval", type=int, nargs=2,
                        default=config.REPOSITORY_INTERVAL,
                        help="id interval")
    parser.add_argument("-e", "--retry-errors", action='store_true',
                        help="retry errors")
    parser.add_argument("-c", "--count", action='store_true',
                        help="count results")
    parser.add_argument('-r', '--reverse', action='store_true',
                        help='iterate in reverse order')
    parser.add_argument('--check', type=str, nargs='*',
                        default={'all', script_name, script_name + '.py'},
                        help='check name in .exit')

    args = parser.parse_args()
    config.VERBOSE = args.verbose
    status = None
    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    with connect() as session, savepid():
        apply(
            session,
            status,
            args.repositories or True,
            0 if args.retry_errors else consts.R_P_ERROR,
            args.count,
            args.interval,
            args.reverse,
            set(args.check)
        )


if __name__ == "__main__":
    main()
