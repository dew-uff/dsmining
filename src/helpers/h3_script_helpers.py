import sys
import os

from src import consts
from src.helpers.h1_utils import vprint

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)
from src.db.database import Repository, Cell, PythonFile


def filter_repositories(session, selected_repositories,
                        skip_if_error, count, interval, reverse, skip_already_processed):
    filters = [
        Repository.processed.op("&")(skip_already_processed) == 0,
        Repository.processed.op("&")(skip_if_error) == 0,
    ]

    if selected_repositories is not True:
        filters += [Repository.id.in_(selected_repositories[:30])]
        selected_repositories = selected_repositories[30:]
    else:
        selected_repositories = False
        if interval:
            filters += [
                Repository.id >= interval[0],
                Repository.id <= interval[1],
            ]

    query = session.query(Repository).filter(*filters)
    if count:
        print(query.count())
        return

    if reverse:
        query = query.order_by(Repository.id.desc())
    else:
        query = query.order_by(Repository.id.asc())
    return selected_repositories, query

def filter_markdown_cells(session, skip_if_error, count, interval,
                 reverse, skip_already_processed):
    filters = [
        Cell.processed.op('&')(skip_already_processed) == 0,
        Cell.processed.op('&')(skip_if_error) == 0,
        Cell.cell_type == 'markdown',
    ]

    if interval:
        filters += [
            Cell.repository_id >= interval[0],
            Cell.repository_id <= interval[1],
        ]

    query = (session.query(Cell) .filter(*filters))

    if count:
        print(query.count())
        return

    if reverse:
        query = query.order_by(
            Cell.repository_id.desc(),
            Cell.notebook_id.asc(),
            Cell.index.asc(),
        )
    else:
        query = query.order_by(
            Cell.repository_id.asc(),
            Cell.notebook_id.asc(),
            Cell.index.asc(),
        )

    return query


def filter_code_cells(session, selected_notebooks,
                      skip_if_error, skip_if_syntaxerror, skip_if_timeout,
                      count, interval, reverse, skip_already_processed):
    filters = [
        Cell.processed.op('&')(skip_already_processed) == 0,
        Cell.processed.op('&')(skip_if_error) == 0,
        Cell.processed.op('&')(skip_if_syntaxerror) == 0,
        Cell.processed.op('&')(skip_if_timeout) == 0,
        Cell.processed.op('&')(consts.C_UNKNOWN_VERSION) == 0,  # known version
        Cell.cell_type == 'code',
        Cell.python.is_(True),
    ]
    if selected_notebooks is not True:
        filters += [
            Cell.notebook_id.in_(selected_notebooks[:30])
        ]
        selected_notebooks = selected_notebooks[30:]
    else:
        selected_notebooks = False
        if interval:
            filters += [
                Cell.repository_id >= interval[0],
                Cell.repository_id <= interval[1],
            ]

    query = (
        session.query(Cell)
        .filter(*filters)
    )

    if count:
        print(query.count())
        return

    if reverse:
        query = query.order_by(
            Cell.repository_id.desc(),
            Cell.notebook_id.asc(),
            Cell.index.asc(),
        )
    else:
        query = query.order_by(
            Cell.repository_id.asc(),
            Cell.notebook_id.asc(),
            Cell.index.asc(),
        )

    return selected_notebooks, query


def filter_python_files(session, selected_python_files,
                     skip_if_error, skip_if_syntaxerror, skip_if_timeout,
                     count, interval, reverse, skip_already_processed):
    filters = [
        PythonFile.processed.op('&')(skip_already_processed) == 0,
        PythonFile.processed.op('&')(skip_if_error) == 0,
        PythonFile.processed.op('&')(skip_if_syntaxerror) == 0,
        PythonFile.processed.op('&')(consts.PF_EMPTY) == 0,
        PythonFile.processed.op('&')(skip_if_timeout) == 0
    ]

    if selected_python_files is not True:
        filters += [
            PythonFile.notebook_id.in_(selected_python_files[:30])
        ]
        selected_python_files = selected_python_files[30:]
    else:
        selected_python_files = False
        if interval:
            filters += [
                PythonFile.repository_id >= interval[0],
                PythonFile.repository_id <= interval[1],
            ]

    query = (
        session.query(PythonFile)
        .filter(*filters)
    )

    if count:
        print(query.count())
        return

    if reverse:
        query = query.order_by(
            PythonFile.repository_id.desc(),
        )
    else:
        query = query.order_by(
            PythonFile.repository_id.asc()
        )

    return selected_python_files, query

def broken_link(notebook_file, repository_id):
    import textwrap
    vprint(3, "Notebook is broken link. Use the following SQL to fix:")
    text = (textwrap.dedent("""\
                select notebooks_count, (char_length(newtext) - char_length(replace(newtext, '''', ''))), concat(
                    'update repositories ',
                    'set notebooks_count = ',
                    (char_length(newtext) - char_length(replace(newtext, ';', ''))) + 1,
                    ', notebooks = ''',
                    newtext,
                    ''' where id = ',
                    id,
                    ';'
                ) from (
                    select id, notebooks_count, replace(
                        replace(
                            replace(
                                notebooks,
                                '{0};', ''
                            ),
                            ';{0}', ''
                        ),
                        '''', ''''''
                    ) as newtext
                    from repositories where id = {1}
                ) as foo;
                """.format(notebook_file, repository_id)))
    text = " ".join(x.strip() for x in text.split("\n"))
    print(text)


def cell_output_formats(cell):
    """Generates output formats from code cells"""
    if cell.get("cell_type") != "code":
        return
    for output in cell.get("outputs", []):
        if output.get("output_type") in {"display_data", "execute_result"}:
            for data_type in output.get("data", []):
                yield data_type
        elif output.get("output_type") == "error":
            yield "error"