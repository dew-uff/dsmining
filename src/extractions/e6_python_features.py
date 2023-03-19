""" Extracts features from Python Files"""

import os
import argparse
import src.config as config
import src.consts as consts

from future.utils.surrogateescape import register_surrogateescape
from src.db.database import PythonFileModule, connect, PythonFileDataIO
from src.helpers.h1_utils import vprint, StatusLogger, check_exit, savepid
from src.helpers.h1_utils import TimeoutError, SafeSession, mount_basedir
from src.helpers.h3_script_helpers import filter_python_files, load_repository
from src.helpers.h3_script_helpers import load_files, extract_features


def process_python_file(
    session, repository_id, python_file, checker,
    skip_if_error=consts.PF_PROCESS_ERROR,
    skip_if_syntaxerror=consts.PF_SYNTAX_ERROR,
    skip_if_timeout=consts.PF_TIMEOUT,
):
    """ Processes Python File to collect features """
    if python_file.processed & consts.PF_PROCESS_OK:
        return 'already processed'

    retry = False
    retry |= not skip_if_error and python_file.processed & consts.PF_PROCESS_ERROR
    retry |= not skip_if_syntaxerror and python_file.processed & consts.PF_SYNTAX_ERROR
    retry |= not skip_if_timeout and python_file.processed & consts.PF_TIMEOUT

    if retry:
        deleted = (
            session.query(PythonFileModule).filter(
                PythonFileModule.python_file_id == python_file.id
            ).delete()
            + session.query(PythonFileDataIO).filter(
                PythonFileDataIO.python_file_id == python_file.id
            ).delete()
        )

        if deleted:
            vprint(2, "Deleted {} rows".format(deleted))
        if python_file.processed & consts.PF_PROCESS_ERROR:
            python_file.processed -= consts.PF_PROCESS_ERROR
        if python_file.processed & consts.PF_SYNTAX_ERROR:
            python_file.processed -= consts.PF_SYNTAX_ERROR
        if python_file.processed & consts.PF_TIMEOUT:
            python_file.processed -= consts.PF_TIMEOUT
        session.add(python_file)

    try:
        vprint(2, "Extracting features")
        try:
            modules, data_ios = extract_features(python_file.source, checker)
        except TimeoutError:
            python_file.processed |= consts.PF_TIMEOUT
            return 'Failed due to  Time Out Error.'
        except SyntaxError:
            python_file.processed |= consts.PF_SYNTAX_ERROR
            return 'Failed due to Syntax Error.'

        vprint(2, "Adding session objects")
        for line, import_type, module_name, local in modules:
            session.add(PythonFileModule(
                repository_id=repository_id,
                python_file_id=python_file.id,

                line=line,
                import_type=import_type,
                module_name=module_name,
                local=local,
            ))

        for line, type_, caller, \
                function_name, function_type,\
                source, source_type in data_ios:
            session.add(PythonFileDataIO(
                repository_id=repository_id,
                python_file_id=python_file.id,

                line=line,
                type=type_,
                caller=caller,
                function_name=function_name,
                function_type=function_type,
                source=source,
                source_type=source_type
            ))

        python_file.processed |= consts.PF_PROCESS_OK
        return "done"
    except Exception as err:
        python_file.processed |= consts.PF_PROCESS_ERROR
        if config.VERBOSE > 4:
            import traceback
            traceback.print_exc()
        return 'Failed to process ({})'.format(err)
    finally:
        session.add(python_file)


def apply(
    session, status, selected_python_files,
    skip_if_error, skip_if_syntaxerror, skip_if_timeout,
    count, interval, reverse, check
):
    """ Extracts python files' features"""
    while selected_python_files:

        selected_python_files, query = filter_python_files(
            session=session, selected_python_files=selected_python_files,
            skip_if_error=skip_if_error, skip_if_syntaxerror=skip_if_syntaxerror,
            skip_if_timeout=skip_if_timeout, count=count, interval=interval,
            reverse=reverse, skip_already_processed=consts.PF_PROCESS_OK)

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

            with mount_basedir():

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

                vprint(2, 'Processing python file: {}'.format(python_file))
                result = process_python_file(
                    session, repository_id, python_file, checker,
                    skip_if_error, skip_if_syntaxerror, skip_if_timeout,
                )
                vprint(2, result)
            status.count += 1
        session.commit()


def main():
    """Main function"""
    register_surrogateescape()
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(
        description='Execute repositories')
    parser.add_argument('-v', '--verbose', type=int, default=config.VERBOSE,
                        help='increase output verbosity')
    parser.add_argument("-n", "--python_files", type=int, default=None,
                        nargs="*",
                        help="python_files ids")
    parser.add_argument('-e', '--retry-errors', action='store_true',
                        help='retry errors')
    parser.add_argument('-s', '--retry-syntaxerrors', action='store_true',
                        help='retry syntax errors')
    parser.add_argument('-t', '--retry-timeout', action='store_true',
                        help='retry timeout')
    parser.add_argument('-i', '--interval', type=int, nargs=2,
                        default=config.REPOSITORY_INTERVAL,
                        help='repository id interval')
    parser.add_argument('-c', '--count', action='store_true',
                        help='count results')
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

    with savepid():
        with connect() as session:
            apply(
                SafeSession(session),
                status,
                args.python_files or True,
                0 if args.retry_errors else consts.PF_PROCESS_ERROR,
                0 if args.retry_syntaxerrors else consts.PF_SYNTAX_ERROR,
                0 if args.retry_timeout else consts.PF_TIMEOUT,
                args.count,
                args.interval,
                args.reverse,
                set(args.check)
            )


if __name__ == '__main__':
    main()
