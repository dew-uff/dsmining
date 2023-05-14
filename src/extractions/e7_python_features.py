""" Extracts features from Python Files"""

import os
import argparse
from itertools import groupby
import src.config.consts as consts

from future.utils.surrogateescape import register_surrogateescape
from src.db.database import PythonFileModule, connect, PythonFileDataIO
from src.helpers.h3_utils import vprint, check_exit, savepid, extract_features, get_next_pyexec, invoke
from timeout_decorator import TimeoutError  # noqa: F401
from src.classes.c2_status_logger import StatusLogger
from src.classes.c1_safe_session import SafeSession
from src.helpers.h2_script_helpers import set_up_argument_parser
from src.helpers.h4_filters import filter_python_files
from src.helpers.h5_loaders import load_files, load_repository

from src.config.states import PF_LOADED, PF_PROCESSED, PF_SYNTAX_ERROR
from src.config.states import PF_PROCESS_ERROR, PF_PROCESS_TIMEOUT
from src.config.states import PF_ORDER, PF_ERRORS
from src.config.states import states_after


def process_python_file(
    session, dispatches, repository_id, python_file, checker,
    retry_error=False, retry_syntax_error=False, retry_timeout=False
):
    """ Processes Python File to collect features """

    if (retry_error and python_file.state == PF_PROCESS_ERROR) or \
            (retry_syntax_error and python_file.state == PF_SYNTAX_ERROR) or \
            (retry_timeout and python_file.state == PF_PROCESS_TIMEOUT):

        deleted = (session.query(PythonFileModule).filter(PythonFileModule.python_file_id == python_file.id).delete() +
                   session.query(PythonFileDataIO).filter(PythonFileDataIO.python_file_id == python_file.id).delete())

        if deleted:
            vprint(2, "Deleted {} rows".format(deleted))
        python_file.state = PF_LOADED
        session.add(python_file)

    elif python_file.state == PF_PROCESSED \
            or python_file.state in PF_ERRORS \
            or python_file.state in states_after(PF_PROCESSED, PF_ORDER):
        return 'already processed'

    try:
        vprint(2, "Extracting features")
        try:
            modules, data_ios, \
                extracted_args, missed_args = extract_features(python_file.source, checker)
        except TimeoutError:
            python_file.state = PF_PROCESS_TIMEOUT
            return 'Failed due to  Time Out Error.'
        except SyntaxError:
            try:
                pyexec = get_next_pyexec()
                dispatches.add((python_file.id, pyexec))
                return 'Dispatched to {}.'.format(pyexec)
            except Exception:  # noqa
                python_file.state = PF_SYNTAX_ERROR
                return 'Failed due to Syntax Error.'

        vprint(2, "Adding session objects")
        for line, import_type, module_name, local in modules:
            session.add(
                PythonFileModule(
                    repository_id=repository_id,
                    python_file_id=python_file.id,

                    line=line,
                    import_type=import_type,
                    module_name=module_name,
                    local=local,
                )
            )

        for line,  caller, \
                function_name, function_type, source, mode in data_ios:

            session.add(
                PythonFileDataIO(
                    repository_id=repository_id,
                    python_file_id=python_file.id,

                    line=line,
                    caller=caller,
                    function_name=function_name,
                    function_type=function_type,
                    source=source,
                    mode=mode,
                )
            )

        python_file.extracted_args = extracted_args
        python_file.missed_args = missed_args
        python_file.state = PF_PROCESSED
        return "done"
    except Exception as err:
        python_file.state = PF_PROCESS_ERROR
        if consts.VERBOSE > 4:
            import traceback
            traceback.print_exc()
        return 'Failed to process ({})'.format(err)
    finally:
        session.add(python_file)


def apply(
    session, status, dispatches, selected_python_files,
    selected_repositories, retry_error, retry_syntax_error,
    retry_timeout, count, interval, reverse, check
):
    """Aggregate Python Files' features"""

    query = filter_python_files(
        session=session, selected_python_files=selected_python_files,
        selected_repositories=selected_repositories,
        count=count, interval=interval, reverse=reverse
    )

    skip_repo = False
    repository_id = None
    repository = None
    archives = None

    skip_python_file = False
    checker = None

    for python_file in query:

        if check_exit(check):
            session.commit()
            vprint(0, 'Found .exit file. Exiting')
            return
        status.report()

        skip_repo, repository_id, repository, archives = load_repository(
            session, python_file, skip_repo, repository_id, repository, archives
        )
        if skip_repo:
            continue

        skip_repo, skip_python_file, python_file_id, archives, checker = load_files(
            session, python_file, repository,
            skip_repo, skip_python_file, archives, checker
        )

        if skip_repo or skip_python_file:
            continue

        vprint(2, 'Processing Python File: {}'.format(python_file))

        result = process_python_file(
            session, dispatches, repository_id, python_file, checker,
            retry_error, retry_syntax_error, retry_timeout
        )

        vprint(2, result)

        status.count += 1
    session.commit()


def pos_apply(dispatches, retry_errors, retry_timeout, verbose):
    """Dispatch execution to other python versions"""
    key = lambda x: x[1] # noqa
    dispatches = sorted(list(dispatches), key=key)
    for pyexec, disp in groupby(dispatches, key=key):
        vprint(0, "Retrying to extract with {}".format(pyexec))
        extra = []
        if retry_errors:
            extra.append("-e")
        if retry_timeout:
            extra.append("-t")
        extra.append("-p")

        python_files_ids = [x[0] for x in disp]
        while python_files_ids:
            ids = python_files_ids[:20000]
            args = extra + ids
            invoke(pyexec, "-u", __file__, "-v", verbose, *args)
            python_files_ids = python_files_ids[20000:]


def main():
    """Main function"""
    register_surrogateescape()
    script_name = os.path.basename(__file__)[:-3]

    parser = argparse.ArgumentParser(description='Execute repositories')
    parser = set_up_argument_parser(parser, script_name, "python_files")
    parser.add_argument("-p", "--python-files", type=int, default=None,
                        nargs="*", help="python files ids")
    args = parser.parse_args()

    consts.VERBOSE = args.verbose
    status = None
    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    dispatches = set()
    with savepid():
        with connect() as session:
            apply(
                session=SafeSession(session),
                status=status,
                dispatches=dispatches,
                selected_python_files=args.python_files,
                selected_repositories=args.repositories,
                retry_error=True if args.retry_errors else False,
                retry_syntax_error=0 if args.retry_syntaxerrors else False,
                retry_timeout=0 if args.retry_timeout else False,
                count=args.count,
                interval=args.interval,
                reverse=args.reverse,
                check=set(args.check)
            )

            if bool(dispatches):
                pos_apply(
                    dispatches,
                    args.retry_errors,
                    args.retry_timeout,
                    args.verbose
                )


if __name__ == '__main__':
    main()
