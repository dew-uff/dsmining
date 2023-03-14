import sys
import os

from src.helpers.h1_utils import vprint

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