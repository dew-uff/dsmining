import sys
import os
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)
from src.db.database import Repository

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
