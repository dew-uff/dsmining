""" Extracts features from markdown cells """

import os
import argparse
import src.config as config

from langdetect import detect
from nltk.corpus import stopwords
from nbconvert.filters.markdown_mistune import MarkdownWithMath
from src.db.database import CellMarkdownFeature, connect
from src.helpers.h1_utils import vprint, StatusLogger, check_exit, savepid
from src.classes.c1_renderer import CountRenderer, LANG_MAP
from src.helpers.h3_script_helpers import filter_markdown_cells
from src.states import *


def extract_features(text):
    """ Extract Features from Markdown Cells """
    language = 'undetected'

    try:
        language = LANG_MAP[detect(text)]
        stopwords_set = stopwords.words(language)
        using_stopwords = True
    except Exception:
        stopwords_set = set()
        using_stopwords = False

    renderer = CountRenderer(language, stopwords_set, using_stopwords)
    markdown = MarkdownWithMath(renderer=renderer, escape=False)
    markdown(text)

    renderer.counter['len'] = len(text)
    renderer.counter['lines'] = len(text.split('\n'))
    words = text.split()
    renderer.counter['words'] = len(words)
    renderer.counter['stopwords'] = sum(1 for word in words if word in stopwords_set)

    renderer.counter['meaningful_lines'] = sum(
        value for key, value in renderer.counter.items()
        if key.endswith('_lines')
    )

    return renderer.counter


def process_markdown_cell(session, repository_id, notebook_id, cell, retry=False):
    """ Processes Markdown Cells to collect features """

    if retry and cell.state == CELL_PROCESS_ERROR:
        cell_markdown_features = session.query(CellMarkdownFeature).filter(
            CellMarkdownFeature.cell_id == cell.id
        ).first()

        if cell_markdown_features:
            session.delete(cell_markdown_features)
            session.commit()

        cell.state = CELL_LOADED
        session.add(cell)

    elif cell.state == CELL_PROCESSED \
            or cell.state in MARKDOWN_CELL_ERROR \
            or cell.state in states_after(CELL_PROCESSED, CELL_ORDER):
        return 'already processed'

    try:
        data = extract_features(cell.source)
        data['repository_id'] = repository_id
        data['notebook_id'] = notebook_id
        data['cell_id'] = cell.id
        data['index'] = cell.index
        session.add(CellMarkdownFeature(**data))
        cell.state = CELL_PROCESSED
        return 'done'

    except Exception as err:
        cell.state = CELL_PROCESS_ERROR
        return 'Failed to process ({})'.format(err)

    finally:
        session.add(cell)


def apply(session, status, retry,
          count, interval, reverse, check):
    """Extract markdown features"""

    query = filter_markdown_cells(
        session=session,
        count=count,
        interval=interval,
        reverse=reverse,
       )

    repository_id = None
    notebook_id = None

    for cell in query:

        if check_exit(check):
            vprint(0, 'Found .exit file. Exiting')
            return
        status.report()

        if repository_id != cell.repository_id:
            session.commit()
            repository_id = cell.repository_id
            vprint(0, 'Processing repository: {}'.format(repository_id))

        if notebook_id != cell.notebook_id:
            notebook_id = cell.notebook_id
            vprint(1, 'Processing notebook: {}'.format(notebook_id))
        vprint(2, 'Processing cell: {}'.format(cell))

        result = process_markdown_cell(
            session=session,
            repository_id=repository_id,
            notebook_id=notebook_id,
            cell=cell,
            retry=retry
        )
        vprint(2, result)
        status.count += 1
    session.commit()


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(
        description='Execute repositories')

    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        type=int, default=config.VERBOSE)
    parser.add_argument("-e", "--retry-errors", help="retry errors",
                        action="store_true")
    parser.add_argument("-c", "--count", help="count filtered repositories",
                        action="store_true")
    parser.add_argument("-r", "--reverse", help="iterate in reverse order",
                        action="store_true")
    parser.add_argument("-i", "--interval", help="interval",
                        type=int, nargs=2, default=config.REPOSITORY_INTERVAL)
    parser.add_argument("--check", help="check name in .exit", type=str,
                        nargs="*", default={"all", script_name, script_name + ".py"})

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
            retry=True if args.retry_errors else False,
            count=args.count,
            interval=args.interval,
            reverse=args.reverse,
            check=set(args.check)
        )


if __name__ == '__main__':
    main()
