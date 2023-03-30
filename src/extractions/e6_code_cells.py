""" Extracts code features from code cells """

import argparse
import os
import src.config.consts as consts


from itertools import groupby
from future.utils.surrogateescape import register_surrogateescape

from src.helpers.h3_utils import extract_features, invoke
from src.classes.c1_safe_session import SafeSession
from src.helpers.h3_utils import TimeoutError
from src.helpers.h3_utils import vprint, check_exit, savepid
from src.classes.c2_status_logger import StatusLogger
from src.db.database import CellModule, connect, CellDataIO
from src.helpers.h2_script_helpers import set_up_argument_parser
from src.helpers.h4_filters import filter_code_cells
from src.helpers.h5_loaders import load_notebook, load_repository

from src.config.states import CELL_LOADED, CELL_PROCESSED, CELL_PROCESS_ERROR
from src.config.states import CELL_SYNTAX_ERROR, CELL_PROCESS_TIMEOUT
from src.config.states import CELL_ORDER, CELL_ERRORS
from src.config.states import states_after


def process_code_cell(
        session, repository_id, notebook_id, cell, checker,
        retry_error=False, retry_syntax_error=False, retry_timeout=False
):
    """ Processes Code Cells to collect features"""
    if (retry_error and cell.state == CELL_PROCESS_ERROR) or \
            (retry_syntax_error and cell.state == CELL_SYNTAX_ERROR) or \
            (retry_timeout and cell.state == CELL_PROCESS_TIMEOUT):

        deleted = (session.query(CellModule).filter(CellModule.cell_id == cell.id).delete() +
                   session.query(CellDataIO).filter(CellDataIO.cell_id == cell.id).delete())

        if deleted:
            vprint(2, "Deleted {} rows".format(deleted))
        cell.state = CELL_LOADED
        session.add(cell)

    elif cell.state == CELL_PROCESSED \
            or cell.state in CELL_ERRORS \
            or cell.state in states_after(CELL_PROCESSED, CELL_ORDER):
        return 'already processed'

    try:
        vprint(2, "Extracting features")
        try:
            modules, data_ios = extract_features(cell.source, checker)
        except TimeoutError:
            cell.state = CELL_PROCESS_TIMEOUT
            return 'Failed due to  Time Out Error.'
        except SyntaxError:
            cell.state = CELL_SYNTAX_ERROR
            return 'Failed due to Syntax Error.'

        vprint(2, "Adding session objects")
        for line, import_type, module_name, local in modules:
            session.add(
                CellModule(
                    repository_id=repository_id,
                    notebook_id=notebook_id,
                    cell_id=cell.id,
                    index=cell.index,

                    line=line,
                    import_type=import_type,
                    module_name=module_name,
                    local=local,
                )
            )

        for line, type_, caller, \
                function_name, function_type, \
                source, source_type in data_ios:
            session.add(
                CellDataIO(
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
                )
            )

        cell.state = CELL_PROCESSED
        return "done"

    except Exception as err:
        cell.state = CELL_PROCESS_ERROR
        if consts.VERBOSE > 4:
            import traceback
            traceback.print_exc()
        return 'Failed to process ({})'.format(err)
    finally:
        session.add(cell)


def apply(
        session, status, dispatches, selected_notebooks, selected_repositories,
        retry_error, retry_syntax_error, retry_timeout,
        count, interval, reverse, check
):
    """ Extracts code cells features """

    query = filter_code_cells(
        session=session, selected_notebooks=selected_notebooks,
        selected_repositories=selected_repositories,
        count=count, interval=interval, reverse=reverse
    )

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

        skip_repo, repository_id, repository, archives = load_repository(
            session, cell, skip_repo, repository_id, repository, archives
        )
        if skip_repo:
            continue

        skip_repo, skip_notebook, notebook_id, archives, checker = load_notebook(
            session, cell, dispatches, repository,
            skip_repo, skip_notebook, notebook_id, archives, checker
        )

        if skip_repo or skip_notebook:
            continue

        vprint(2, 'Processing cell: {}'.format(cell))

        result = process_code_cell(
            session, repository_id, notebook_id, cell, checker,
            retry_error, retry_syntax_error, retry_timeout,
        )

        vprint(2, result)

        status.count += 1
    session.commit()


def pos_apply(dispatches, retry_errors, retry_timeout, verbose):
    """Dispatch execution to other python versions"""
    key = lambda x: x[1]  # noqa
    dispatches = sorted(list(dispatches), key=key)
    for pyexec, disp in groupby(dispatches, key=key):
        vprint(0, "Dispatching to {}".format(pyexec))
        extra = []
        if retry_errors:
            extra.append("-e")
        if retry_timeout:
            extra.append("-t")
        extra.append("-n")

        notebook_ids = [x[0] for x in disp]
        while notebook_ids:
            ids = notebook_ids[:20000]
            args = extra + ids
            invoke(pyexec, "-u", __file__, "-v", verbose, *args)
            notebook_ids = notebook_ids[20000:]


def main():
    """Main function"""
    register_surrogateescape()
    script_name = os.path.basename(__file__)[:-3]

    parser = argparse.ArgumentParser(description='Execute repositories')
    parser = set_up_argument_parser(parser, script_name, "code_cells")
    parser.add_argument("-n", "--notebooks", type=int, default=None,
                        nargs="*", help="notebooks ids")
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
                selected_notebooks=args.notebooks,
                selected_repositories=args.repositories,
                retry_error=False if args.retry_errors else False,
                retry_syntax_error=False if args.retry_syntaxerrors else False,
                retry_timeout=False if args.retry_timeout else False,
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
