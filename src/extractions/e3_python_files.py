""" Extracts python files from repositories"""

import os
import sys
src_path = os.path.dirname(os.path.abspath(''))
if src_path not in sys.path:
    sys.path.append(src_path)

import argparse
import src.config.consts as consts

from src.db.database import PythonFile, connect
from src.helpers.h3_utils import vprint, savepid
from src.classes.c2_status_logger import StatusLogger
from src.helpers.h3_utils import find_files, unzip_repository, timeout
from src.helpers.h2_script_helpers import apply, set_up_argument_parser

from src.config.states import PF_LOADED, PF_EMPTY, PF_L_ERROR
from src.config.states import REP_PF_EXTRACTED, REP_UNAVAILABLE_FILES
from src.config.states import REP_N_EXTRACTED, REP_ORDER, REP_ERRORS
from src.config.states import states_after, states_before


def find_python_files(session, repository):
    """ Finds all python files in a repository but setup.py """
    python_files = []

    if not repository.path.exists():
        msg = unzip_repository(repository)
        if msg != "done":
            vprint(2, "repository not found")
            repository.state = REP_UNAVAILABLE_FILES
            session.add(repository)
            session.commit()
            return python_files

    files = find_files(repository.path, "*.py")
    for file in files:
        if "/setup.py" not in str(file) \
                and "venv" not in str(file) \
                and "CorePython" not in str(file) \
                and "conda" not in str(file) \
                and str(file) != 'setup.py':
            python_files.append(str(file.relative_to(repository.path)))

    return python_files


@timeout(5 * 60, use_signals=False)
def process_python_files(session, repository, python_files_names, count):

    for name in python_files_names:
        if not name:
            continue

        count += 1

        python_file = session.query(PythonFile).filter(
            PythonFile.repository_id == repository.id,
            PythonFile.name == name,
        ).first()

        if python_file is not None:
            if python_file.state == PF_L_ERROR:
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
                pf_state = PF_EMPTY
            else:
                pf_state = PF_LOADED

            python_file = PythonFile(
                repository_id=repository.id,
                name=name,
                source=source,
                total_lines=total,
                state=pf_state
            )

            session.add(python_file)
        except Exception as err:

            vprint(1, "Failed to load python file {} due {!r}".format(name, err))

            # We mark this python file as broken and keep adding the rest.
            python_file = PythonFile(
                repository_id=repository.id,
                name=name,
                state=PF_L_ERROR
            )
            session.add(python_file)

    return count


def process_repository(session, repository):
    """ Processes repository """

    if repository.state == REP_PF_EXTRACTED \
            or repository.state in REP_ERRORS\
            or repository.state in states_after(REP_PF_EXTRACTED, REP_ORDER):
        return "already processed"
    elif repository.state in states_before(REP_N_EXTRACTED, REP_ORDER):
        return "wrong script order, before you must run {}"\
            .format(states_before(REP_N_EXTRACTED, REP_ORDER))

    count = 0
    repository_python_files_names = find_python_files(session, repository)

    if repository.state is not REP_UNAVAILABLE_FILES:
        try:
            count = process_python_files(session, repository, repository_python_files_names, count)
            repository.state = REP_PF_EXTRACTED
            repository.python_files_count = count
        except Exception:
            vprint(1, "Timed out")

    session.add(repository)
    session.commit()
    return "done"


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]

    parser = argparse.ArgumentParser(
        description="Extract requirement files from registered repositories")
    parser = set_up_argument_parser(parser, script_name)
    args = parser.parse_args()

    consts.VERBOSE = args.verbose
    status = None

    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    with connect() as session, savepid():
        apply(
            session=session,
            status=status,
            selected_repositories=args.repositories,
            retry=True if args.retry_errors else False,
            count=args.count,
            interval=args.interval,
            reverse=args.reverse,
            check=set(args.check),
            process_repository=process_repository,
            model_type='python files',
            params=2
        )


if __name__ == "__main__":
    main()
