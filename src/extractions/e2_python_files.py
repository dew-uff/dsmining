""" Extracts python files from repositories"""

import os
import argparse
import src.config as config
import src.consts as consts

from src.db.database import PythonFile, connect
from src.helpers.h1_utils import vprint, StatusLogger, savepid
from src.helpers.h1_utils import find_files, unzip_repository
from src.helpers.h3_script_helpers import apply
from src.states import *


def find_python_files(session, repository):
    """ Finds all python files in a repository but setup.py """
    python_files = []

    if not repository.path.exists():
        msg = unzip_repository(session, repository)
        if msg != "done":
            vprint(2, "repository not found")
            repository.state = REP_UNAVAILABLE_FILES
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
            else:
                vprint(2, "Python File already processed")
                continue

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


def process_repository(session, repository, retry=False):
    """ Processes repository """

    if retry and repository.state == REP_PF_ERROR:
        session.add(repository)
        vprint(3, "retrying to process {}".format(repository))
        repository.state = REP_N_EXTRACTED
    elif repository.state == REP_PF_EXTRACTED \
            or repository.state in REP_ERRORS\
            or repository.state in states_after(REP_PF_EXTRACTED, REP_ORDER):
        return "already processed"
    elif repository.state in states_before(REP_N_EXTRACTED, REP_ORDER):
        return f'wrong script order, before you must run {states_before(REP_N_EXTRACTED, REP_ORDER)}'

    count = 0
    repository_python_files_names = find_python_files(session, repository)
    count, no_errors = process_python_files(session, repository, repository_python_files_names, count)

    if no_errors:
        repository.state = REP_PF_EXTRACTED
        repository.python_files_count = count
    else:
        repository.state = REP_PF_ERROR

    session.add(repository)
    session.commit()
    return "done"


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
            session=session,
            status=status,
            selected_repositories=args.repositories or True,
            retry=True if args.retry_errors else False,
            count=args.count,
            interval=args.interval,
            reverse=args.reverse,
            check=set(args.check),
            process_repository=process_repository,
            model_type='python files'
        )


if __name__ == "__main__":
    main()
