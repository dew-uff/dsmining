"""Load markdown features"""
import argparse
import os
import src.config as config
import src.consts as consts

from src.db.database import Notebook, connect, NotebookMarkdown, Cell
from src.db.database import Module
from src.helpers.h1_utils import vprint, StatusLogger, check_exit, savepid
from src.helpers.h5_aggregation_helpers import calculate_markdown, calculate_modules


TYPE = "notebook"

def process_notebook(session, notebook, skip_if_error):
    if notebook.processed & consts.N_AGGREGATE_ERROR:
        notebook.processed -= consts.N_AGGREGATE_ERROR
        session.add(notebook)
    if notebook.processed & consts.N_AGGREGATE_OK:
        return "already processed"

    if notebook.kernel == 'no-kernel' and notebook.nbformat == '0':
        notebook.processed |= consts.N_AGGREGATE_OK
        session.add(notebook)
        return "invalid notebook format. Do not aggregate it"

    agg_markdown = calculate_markdown(session, notebook)

    if notebook.markdown_cells != agg_markdown["cell_count"]:
        notebook.processed |= consts.N_AGGREGATE_ERROR
        session.add(notebook)
        return "incomplete markdown analysis"

    if notebook.language != "python":
        session.add(NotebookMarkdown(**agg_markdown))
        notebook.processed |= consts.N_AGGREGATE_OK
        session.add(notebook)
        return "ok - non python notebook"

    syntax_error = bool(list(notebook.cell_objs.filter(
        Cell.processed.op("&")(consts.C_SYNTAX_ERROR) == consts.C_SYNTAX_ERROR
    )))

    if syntax_error:
        session.add(NotebookMarkdown(**agg_markdown))
        notebook.processed |= consts.N_AGGREGATE_OK
        notebook.processed |= consts.N_SYNTAX_ERROR
        session.add(notebook)
        return "ok - syntax error"

    agg_modules = calculate_modules(session, notebook, TYPE)

    session.add(NotebookMarkdown(**agg_markdown))
    session.add(Module(**agg_modules))
    notebook.processed |= consts.N_AGGREGATE_OK
    session.add(notebook)

    return "ok"


def load_repository(session, notebook, repository_id):
    if repository_id != notebook.repository_id:
        try:
            session.commit()
        except Exception as err:
            vprint(0, 'Failed to save modules from repository {} due to {}'.format(
                repository_id, err
            ))

        vprint(0, 'Processing repository: {}'.format(repository_id))
        return notebook.repository_id

    return repository_id


def apply(
    session, status, skip_if_error,
    count, interval, reverse, check
):
    """Extract code cell features"""
    filters = [
        Notebook.processed.op("&")(consts.N_AGGREGATE_OK) == 0,
        Notebook.processed.op("&")(skip_if_error) == 0,
        Notebook.processed.op("&")(consts.N_GENERIC_LOAD_ERROR) == 0,
    ]
    if interval:
        filters += [
            Notebook.repository_id >= interval[0],
            Notebook.repository_id <= interval[1],
        ]

    query = (
        session.query(Notebook)
        .filter(*filters)
    )

    if count:
        print(query.count())
        return

    if reverse:
        query = query.order_by(
            Notebook.repository_id.desc(),
            Notebook.id.desc(),
        )
    else:
        query = query.order_by(
            Notebook.repository_id.asc(),
            Notebook.id.asc(),
        )

    repository_id = None

    for notebook in query:
        if check_exit(check):
            session.commit()
            vprint(0, 'Found .exit file. Exiting')
            return
        status.report()

        repository_id = load_repository(session, notebook, repository_id)

        vprint(1, 'Processing notebook: {}'.format(notebook))
        result = process_notebook(session, notebook, skip_if_error)
        vprint(1, result)
        status.count += 1
    session.commit()


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(
        description='Execute repositories')
    parser.add_argument('-v', '--verbose', type=int, default=config.VERBOSE,
                        help='increase output verbosity')
    parser.add_argument('-e', '--retry-errors', action='store_true',
                        help='retry errors')
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

    with connect() as session, savepid():
        apply(
            session,
            status,
            0 if args.retry_errors else consts.N_AGGREGATE_ERROR,
            args.count,
            args.interval,
            args.reverse,
            set(args.check)
        )

if __name__ == '__main__':
    main()
