""" Extracts code features from code cells """

import argparse
import os
import src.config as config
import src.consts as consts

from src.helpers.h1_utils import mount_basedir
from src.helpers.h1_utils import TimeoutError, SafeSession
from src.helpers.h1_utils import vprint, StatusLogger, check_exit, savepid
from src.db.database import CellModule, connect, CellDataIO
from src.helpers.h3_script_helpers import filter_code_cells, load_repository
from src.helpers.h3_script_helpers import load_notebook, extract_features
from future.utils.surrogateescape import register_surrogateescape


def process_code_cell(
    session, repository_id, notebook_id, cell, checker,
    skip_if_error=consts.C_PROCESS_ERROR,
    skip_if_syntaxerror=consts.C_SYNTAX_ERROR,
    skip_if_timeout=consts.C_TIMEOUT,
):
    """ Processes Code Cells to collect features"""
    if cell.processed & consts.C_PROCESS_OK:
        return 'already processed'

    retry = False
    retry |= (not skip_if_error) and cell.processed & consts.C_PROCESS_ERROR
    retry |= (not skip_if_syntaxerror) and cell.processed & consts.C_SYNTAX_ERROR
    retry |= (not skip_if_timeout) and cell.processed & consts.C_TIMEOUT

    if retry:
        deleted = (
            session.query(CellModule).filter(
                CellModule.cell_id == cell.id
            ).delete()
            + session.query(CellDataIO).filter(
                CellDataIO.cell_id == cell.id
            ).delete()
        )
        if deleted:
            vprint(2, "Deleted {} rows".format(deleted))
        if cell.processed & consts.C_PROCESS_ERROR:
            cell.processed -= consts.C_PROCESS_ERROR
        if cell.processed & consts.C_SYNTAX_ERROR:
            cell.processed -= consts.C_SYNTAX_ERROR
        if cell.processed & consts.C_TIMEOUT:
            cell.processed -= consts.C_TIMEOUT
        session.add(cell)

    try:
        vprint(2, "Extracting features")
        try:
            modules, data_ios = extract_features(cell.source, checker)
        except TimeoutError:
            cell.processed |= consts.C_TIMEOUT
            return 'Failed due to  Time Out Error.'
        except SyntaxError:
            cell.processed |= consts.C_SYNTAX_ERROR
            return 'Failed due to Syntax Error.'

        vprint(2, "Adding session objects")
        for line, import_type, module_name, local in modules:
            session.add(CellModule(
                repository_id=repository_id,
                notebook_id=notebook_id,
                cell_id=cell.id,
                index=cell.index,

                line=line,
                import_type=import_type,
                module_name=module_name,
                local=local,
            ))

        for line, type_, caller,\
                function_name, function_type,\
                source, source_type in data_ios:
            session.add(CellDataIO(
                repository_id=repository_id,
                notebook_id=notebook_id,
                cell_id=cell.id,
                index=cell.index,

                line=line,
                type=type_,
                caller=caller,
                function_name=function_name,
                function_type=function_type,
                source=source,
                source_type=source_type
            ))

        cell.processed |= consts.C_PROCESS_OK
        return "done"

    except Exception as err:
        cell.processed |= consts.C_PROCESS_ERROR
        if config.VERBOSE > 4:
            import traceback
            traceback.print_exc()
        return 'Failed to process ({})'.format(err)
    finally:
        session.add(cell)


def apply(
    session, status, selected_notebooks,
    skip_if_error, skip_if_syntaxerror, skip_if_timeout,
    count, interval, reverse, check
):
    """ Extracts code cells features """
    while selected_notebooks:

        selected_notebooks, query = filter_code_cells(
            session=session, selected_notebooks=selected_notebooks,
            skip_if_error=skip_if_error, skip_if_syntaxerror=skip_if_syntaxerror,
            skip_if_timeout=skip_if_timeout, count=count, interval=interval,
            reverse=reverse, skip_already_processed=consts.C_PROCESS_OK)

        skip_repo = False
        repository_id = None
        repository = None
        archives = None

        skip_notebook = False
        notebook_id = None
        checker = None

        for cell in query:

            if check_exit(check):
                session.commit()
                vprint(0, 'Found .exit file. Exiting')
                return
            status.report()

            with mount_basedir():

                skip_repo, repository_id, repository, archives = load_repository(
                    session, cell, skip_repo, repository_id, repository, archives
                )
                if skip_repo:
                    continue

                skip_repo, skip_notebook, notebook_id, archives, checker = load_notebook(
                    session, cell, repository, skip_repo, skip_notebook, notebook_id, archives, checker)

                if skip_repo or skip_notebook:
                    continue

                vprint(2, 'Processing cell: {}'.format(cell))

                result = process_code_cell(
                    session, repository_id, notebook_id, cell, checker,
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
    parser.add_argument("-n", "--notebooks", type=int, default=None,
                        nargs="*",
                        help="notebooks ids")
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
                args.notebooks or True,
                0 if args.retry_errors else consts.C_PROCESS_ERROR,
                0 if args.retry_syntaxerrors else consts.C_SYNTAX_ERROR,
                0 if args.retry_timeout else consts.C_TIMEOUT,
                args.count,
                args.interval,
                args.reverse,
                set(args.check)
            )


if __name__ == '__main__':
    main()
