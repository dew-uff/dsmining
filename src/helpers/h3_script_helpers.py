import sys
import os
import tarfile
import ast

from src import consts
from src.classes.c2_local_checkers import SetLocalChecker, CompressedLocalChecker, PathLocalChecker
from src.classes.c3_cell_visitor import CellVisitor
from src.helpers.h1_utils import vprint, to_unicode

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)
from src.db.database import Repository, Cell, PythonFile, RepositoryFile
import src.extractions.e8_extract_files as e8
from src.helpers.h1_utils import timeout

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




def load_archives(session, repository):
    if not repository.processed & consts.R_EXTRACTED_FILES:

        if repository.zip_path.exists():
            vprint(1, 'Extracting files')
            result = e8.process_repository(session, repository, skip_if_error=0)

            try:
                session.commit()
                if result != "done":
                    raise Exception("Extraction failure. Fallback")
                vprint(1, result)

            except Exception as err:
                vprint(1, 'Failed: {}'.format(err))
                try:
                    tarzip = tarfile.open(str(repository.zip_path))
                    if repository.processed & consts.R_COMPRESS_ERROR:
                        repository.processed -= consts.R_COMPRESS_ERROR
                    session.add(repository)
                except tarfile.ReadError:
                    repository.processed |= consts.R_COMPRESS_ERROR
                    session.add(repository)
                    return True, None
                zip_path = to_unicode(repository.hash_dir2)
                return False, (tarzip, zip_path)

        elif repository.path.exists():
            repo_path = to_unicode(repository.path)
            return False, (None, repo_path)
        else:
            repository.processed |= consts.R_UNAVAILABLE_FILES
            session.add(repository)
            vprint(1, "Failed to load repository. Skipping")
            return True, None

    tarzip = {
        fil.path for fil in session.query(RepositoryFile).filter(
            RepositoryFile.repository_id == repository.id
        )
    }
    zip_path = ""
    if tarzip:
        return False, (tarzip, zip_path)

    return True, None


def load_files(
    session, file, repository,
    skip_repo, skip_file, archives, checker
):
    if archives == "todo":
        skip_repo, archives = load_archives(session, repository)
        if skip_repo:
            return skip_repo, skip_file, file.id, archives, None

    if archives is None:
        return True, True, file.id, archives, None

    vprint(1, 'Processing file: {}'.format(file))
    name = to_unicode(file.name)

    tarzip, repo_path = archives
    file_path = os.path.join(repo_path, name)

    try:

        if isinstance(tarzip, set):
            checker = SetLocalChecker(tarzip, file_path)
        elif tarzip:
            checker = CompressedLocalChecker(tarzip, file_path)
        else:
            checker = PathLocalChecker(file_path)

        if not checker.exists(file_path):
            raise Exception("Repository content problem. File not found")

        return skip_repo, False, file.id, archives, checker

    except Exception as err:
        vprint(2, "Failed to load file {} due to {}".format(file, err))
        return skip_repo, True, file.id, archives, checker

def load_notebook(
    session, cell, repository,
    skip_repo, skip_notebook, notebook_id, archives, checker
):
    if notebook_id != cell.notebook_id:
        notebook = cell.notebook_obj

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

    return skip_repo, skip_notebook, notebook_id, archives, checker

def load_repository(session, file, skip_repo, repository_id,
                    repository, archives):

    if repository_id != file.repository_id:
        repository = file.repository_obj
        success, msg = session.commit()
        if not success:
            vprint(0, 'Failed to save files from repository {} due to {}'.format(
                repository, msg
            ))

        vprint(0, 'Processing repository: {}'.format(repository))
        return False, file.repository_id, repository, "todo"

    return skip_repo, repository_id, repository, archives


@timeout(1 * 60, use_signals=False)
def extract_features(text, checker):
    """Use cell visitor to extract features from cell text"""
    visitor = CellVisitor(checker)
    try:
        parsed = ast.parse(text)
    except ValueError:
        raise SyntaxError("Invalid escape")
    visitor.visit(parsed)

    return visitor.modules, visitor.data_ios

