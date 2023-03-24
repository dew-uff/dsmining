from src.db.database import Repository, Cell, PythonFile
from src.states import CELL_UNKNOWN_VERSION, PF_EMPTY


def filter_repositories(session, selected_repositories,
                        count, interval, reverse):
    filters = []

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


def filter_markdown_cells(session, count, interval, reverse):
    filters = [
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
                      count, interval, reverse):
    filters = [
        Cell.state is not CELL_UNKNOWN_VERSION,  # known version
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

    query = (session.query(Cell).filter(*filters))

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
                        count, interval, reverse):
    filters = [
        PythonFile.processed.op('&')(PF_EMPTY) == 0,
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
