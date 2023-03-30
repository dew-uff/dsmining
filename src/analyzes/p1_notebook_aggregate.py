"""Load markdown features"""
import argparse
import os
import src.config.consts as consts

from src.db.database import connect, NotebookMarkdown, Cell
from src.db.database import Module
from src.helpers.h2_script_helpers import set_up_argument_parser
from src.helpers.h3_utils import vprint, check_exit, savepid
from src.classes.c2_status_logger import StatusLogger
from src.helpers.h4_filters import filter_notebooks
from src.helpers.h6_aggregation_helpers import calculate_markdown, calculate_modules, load_repository
from src.config.states import *

TYPE = "notebook"


def process_notebook(session, notebook, retry=False):
    if retry and notebook.state == NB_AGGREGATE_ERROR:
        vprint(3, "retrying to process {}".format(notebook))
        notebook.state = NB_LOADED
        session.add(notebook)
    elif notebook.state == NB_AGGREGATED \
            or notebook.state == NB_AGGR_MARKDOWN\
            or notebook.state in NB_ERRORS:
        return "already processed"

    if notebook.kernel == 'no-kernel' and notebook.nbformat == '0':
        notebook.state = NB_INVALID
        session.add(notebook)
        return "invalid notebook format. Do not aggregate it"

    agg_markdown = calculate_markdown(notebook)

    if notebook.markdown_cells != agg_markdown["cell_count"]:
        notebook.state = NB_AGGREGATE_ERROR
        session.add(notebook)
        return "incomplete markdown analysis"

    if notebook.language != "python":
        session.add(NotebookMarkdown(**agg_markdown))
        notebook.state = NB_AGGR_MARKDOWN
        session.add(notebook)
        return "ok - non python notebook"

    syntax_error = bool(
        list(
            notebook.cell_objs.filter(Cell.state == CELL_SYNTAX_ERROR)
        )
    )

    if syntax_error:
        session.add(NotebookMarkdown(**agg_markdown))
        notebook.state = NB_AGGR_MARKDOWN
        session.add(notebook)
        return "ok - syntax error"

    agg_modules = calculate_modules(notebook, TYPE)

    session.add(NotebookMarkdown(**agg_markdown))
    session.add(Module(**agg_modules))

    notebook.state = NB_AGGREGATED
    session.add(notebook)

    return "ok"


def apply(
    session, status, retry,
    count, interval, reverse, check
):
    """Aggregate Notebook features"""

    query = filter_notebooks(session=session, count=count,
                             interval=interval, reverse=reverse)

    repository_id = None

    for notebook in query:
        if check_exit(check):
            session.commit()
            vprint(0, 'Found .exit file. Exiting')
            return
        status.report()

        repository_id = load_repository(session, notebook, repository_id)

        vprint(1, 'Processing notebook: {}'.format(notebook))
        result = process_notebook(session, notebook, retry)
        vprint(1, result)
        status.count += 1
    session.commit()


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(description="Aggregates features from Notebooks' Cells")
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
            retry=True if args.retry_errors else False,
            count=args.count,
            interval=args.interval,
            reverse=args.reverse,
            check=set(args.check)
        )


if __name__ == '__main__':
    main()
