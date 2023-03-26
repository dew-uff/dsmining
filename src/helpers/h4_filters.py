from src.db.database import Repository, Cell, PythonFile, Notebook
from src.states import CELL_UNKNOWN_VERSION, PF_EMPTY, NB_GENERIC_LOAD_ERROR


def filter_repositories(session, selected_repositories,
                        count, interval, reverse):
    filters = []

    if selected_repositories:
        filters += [Repository.id.in_(selected_repositories)]

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
    return query


def filter_markdown_cells(session, count, selected_repositories,
                          interval, reverse):
    filters = [
        Cell.cell_type == 'markdown',
    ]

    if selected_repositories:
        filters += [Cell.repository_id.in_(selected_repositories)]

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


def filter_code_cells(session, selected_repositories,
                      count, interval, reverse):
    filters = [
        Cell.state != CELL_UNKNOWN_VERSION,  # known version
        Cell.cell_type == 'code',
        Cell.python.is_(True),
    ]

    if selected_repositories:
        filters += [Cell.repository_id.in_(selected_repositories)]

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

    return query


def filter_python_files(session, selected_repositories,
                        count, interval, reverse):
    filters = [
        PythonFile.state != PF_EMPTY
    ]

    if selected_repositories:
        filters += [PythonFile.repository_id.in_(selected_repositories)]
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

    return query


def filter_notebooks(session, count, interval, reverse):
    filters = [
        Notebook.state != NB_GENERIC_LOAD_ERROR
    ]

    if interval:
        filters += [
            Notebook.repository_id >= interval[0],
            Notebook.repository_id <= interval[1],
        ]

    query = (session.query(Notebook).filter(*filters))

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

    return query
