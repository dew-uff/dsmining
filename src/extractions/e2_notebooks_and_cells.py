""" Extracts notebooks and their cells from repositories"""

import os
import argparse
import nbformat as nbf
import src.consts as consts

from IPython.core.interactiveshell import InteractiveShell
from src.db.database import Cell, Notebook, connect
from src.helpers.h3_utils import savepid, unzip_repository, cell_output_formats
from src.classes.c1_safe_session import SafeSession
from src.helpers.h3_utils import find_files, TimeoutError, vprint
from src.classes.c2_status_logger import StatusLogger
from src.helpers.h2_script_helpers import apply, set_up_argument_parser

from src.config.states import NB_LOADED, NB_LOAD_ERROR, NB_STOPPED
from src.config.states import NB_LOAD_FORMAT_ERROR, NB_LOAD_TIMEOUT
from src.config.states import NB_LOAD_SYNTAX_ERROR, NB_GENERIC_LOAD_ERROR
from src.config.states import CELL_LOADED, CELL_SYNTAX_ERROR, CELL_UNKNOWN_VERSION
from src.config.states import REP_LOADED, REP_N_ERROR, REP_UNAVAILABLE_FILES
from src.config.states import REP_N_EXTRACTED, REP_ORDER, REP_ERRORS
from src.config.states import states_after, states_before


def load_cells(repository_id, nbrow, notebook, status):
    shell = InteractiveShell.instance()
    is_python = nbrow["language"] == "python"
    is_unknown_version = nbrow["language_version"] == "unknown"

    cells = notebook["cells"]
    cells_info = []
    exec_count = -1

    for index, cell in enumerate(cells):
        vprint(3, "Loading cell {}".format(index))

        cell_exec_count = cell.get("execution_count") or -1
        if isinstance(cell_exec_count, str) and cell_exec_count.isdigit():
            cell_exec_count = int(cell_exec_count)
        if isinstance(cell_exec_count, int):
            exec_count = max(exec_count, cell_exec_count)
        output_formats = ";".join(set(cell_output_formats(cell)))

        cell_state = CELL_LOADED
        if is_unknown_version:
            cell_state = CELL_UNKNOWN_VERSION

        try:
            source = cell["source"] = cell["source"] or ""
            if is_python and cell.get("cell_type") == "code":
                try:
                    source = shell.input_transformer_manager.transform_cell(source)
                except (IndentationError, SyntaxError) as err:
                    vprint(3, "Error on cell transformation: {}".format(err))
                    source = ""
                    status = NB_LOAD_SYNTAX_ERROR
                    cell_state = CELL_SYNTAX_ERROR
                if "\0" in source:
                    vprint(3, "Found null byte in source. Replacing it by \\n")
                    source = source.replace("\0", "\n")

            cellrow = {
                "repository_id": repository_id,
                "notebook_id": None,
                "index": index,
                "cell_type": cell.get("cell_type", "<unknown>"),
                "execution_count": cell.get("execution_count"),
                "lines": cell["source"].count("\n") + 1,
                "output_formats": output_formats,
                "source": source,
                "python": is_python,
                "state": cell_state,
            }
            cells_info.append(cellrow)

            nbrow["total_cells"] += 1
            if cell.get("cell_type") == "code":
                nbrow["code_cells"] += 1
                if output_formats:
                    nbrow["code_cells_with_output"] += 1
            elif cell.get("cell_type") == "markdown":
                nbrow["markdown_cells"] += 1
            elif cell.get("cell_type") == "raw":
                nbrow["raw_cells"] += 1
            else:
                nbrow["unknown_cell_formats"] += 1
            if not cell["source"].strip():
                nbrow["empty_cells"] += 1

        except KeyError as err:
            vprint(3, "Error on cell extraction: {}".format(err))
            status = NB_LOAD_FORMAT_ERROR

    return nbrow, cells_info, exec_count, status


# @timeout(5 * 60, use_signals=False)
def load_notebook(repository_id, path, notebook_file, nbrow):
    """ Extract notebook information and cells from notebook """
    # pylint: disable=too-many-locals

    status = NB_LOADED

    try:
        with open(str(path / notebook_file)) as ofile:
            notebook = nbf.read(ofile, nbf.NO_CONVERT)

        nbrow["nbformat"] = "{0[nbformat]}".format(notebook)

        if "nbformat_minor" in notebook:
            nbrow["nbformat"] += ".{0[nbformat_minor]}".format(notebook)
        notebook = nbf.convert(notebook, 4)
        metadata = notebook["metadata"]

    except OSError as e:
        vprint(3, "Failed to open notebook {}".format(e))

        nbrow["state"] = NB_LOAD_ERROR
        if os.path.islink(str(path / notebook_file)):
            vprint(3, 'Notebook is broken link')

        return nbrow, []

    except Exception as e:  # pylint: disable=broad-except
        vprint(3, "Failed to load notebook {}".format(e))

        nbrow["state"] = NB_LOAD_FORMAT_ERROR
        return nbrow, []

    nbrow["kernel"] = metadata.get("kernelspec", {}).get("name", "no-kernel")

    language_info = metadata.get("language_info", {})
    nbrow["language"] = language_info.get("name", "unknown")
    nbrow["language_version"] = language_info.get("version", "unknown")

    nbrow, cells_info, exec_count, status \
        = load_cells(repository_id, nbrow, notebook, status)

    if nbrow["total_cells"] == 0:
        status = NB_LOAD_FORMAT_ERROR

    nbrow["max_execution_count"] = exec_count
    nbrow["state"] = status
    return nbrow, cells_info


def process_notebooks(session, repository, repository_notebooks_names):
    count = 0
    for name in repository_notebooks_names:
        if not name:
            continue
        count += 1

        notebook = session.query(Notebook).filter(
            Notebook.repository_id == repository.id,
            Notebook.name == name,
        ).first()

        if notebook is not None:
            if notebook.state == NB_STOPPED:
                session.delete(notebook)
                session.commit()
            else:
                if notebook.state == NB_GENERIC_LOAD_ERROR:
                    count -= 1
                    vprint(2, "Notebook already exists. Delete from DB: {}".format(notebook))
                    with open(str(consts.LOGS_DIR / "todo_delete"), "a") as f:
                        f.write("{},".format(notebook.id))
                else:
                    vprint(2, "Notebook already processed")
                continue  # Skip working notebook

        if not repository.path.exists():
            vprint(2, "Unzipping repository: {}".format(repository.zip_path))
            msg = unzip_repository(repository)
            if msg != "done":
                vprint(2, msg)
                return "failed"

        try:
            vprint(2, "Loading notebook {}".format(name))
            nbrow = {
                "repository_id": repository.id,
                "name": name,
                "nbformat": 0,
                "kernel": "no-kernel",
                "language": "unknown",
                "language_version": "unknown",
                "max_execution_count": 0,
                "total_cells": 0,
                "code_cells": 0,
                "code_cells_with_output": 0,
                "markdown_cells": 0,
                "raw_cells": 0,
                "unknown_cell_formats": 0,
                "empty_cells": 0,
                "state": NB_LOADED,
            }
            try:
                nbrow, cells = load_notebook(repository.id, repository.path, name, nbrow)
            except TimeoutError:
                nbrow["state"] = NB_LOAD_TIMEOUT
                cells = []
            nbrow["state"] = NB_STOPPED
            notebook = Notebook(**nbrow)
            session.dependent_add(
                notebook, [Cell(**cellrow) for cellrow in cells], "notebook_id"
            )

        except Exception as err:  # pylint: disable=broad-except
            repository.state = REP_N_ERROR
            session.add(repository)
            vprint(1, "Failed to load notebook {} due {!r}".format(name, err))
            if consts.VERBOSE > 4:
                import traceback
                traceback.print_exc()
    return count, repository


def find_notebooks(session, repository):
    """ Finds all jupyter notebooks files in a repository """
    notebooks = []

    if not repository.path.exists():
        msg = unzip_repository(repository)
        if msg != "done":
            vprint(2, "repository not found")
            repository.state = REP_UNAVAILABLE_FILES
            session.add(repository)
            session.commit()
            return notebooks

    files = find_files(repository.path, "*.ipynb")
    for file in files:
        if ".ipynb_checkpoints" not in str(file):
            notebooks.append(str(file.relative_to(repository.path)))

    repository.notebooks_count = len(notebooks)
    session.commit()
    return notebooks


def process_repository(session, repository, retry=False):
    """ Processes repository """

    if retry and repository.state == REP_N_ERROR:
        vprint(3, "retrying to process {}".format(repository))
        repository.state = REP_LOADED
        session.add(repository)
    elif repository.state == REP_N_EXTRACTED\
            or repository.state in REP_ERRORS\
            or repository.state in states_after(REP_N_EXTRACTED, REP_ORDER):
        return "already processed"
    elif repository.state in states_before(REP_LOADED, REP_ORDER):
        return "wrong script order, before you must run {}"\
            .format(states_before(REP_LOADED, REP_ORDER))

    repository_notebooks_names = find_notebooks(session, repository)

    if repository.state is not REP_UNAVAILABLE_FILES:
        count, repository = process_notebooks(session, repository, repository_notebooks_names)

        if repository.state != REP_N_ERROR and count == repository.notebooks_count:
            repository.state = REP_N_EXTRACTED
        else:
            repository.state = REP_N_ERROR

    session.add(repository)

    status, err = session.commit()
    if not status:
        if repository.state != REP_N_ERROR:
            repository.state = REP_N_ERROR
        session.add(repository)
        session.commit()
        return "failed due {!r}".format(err)

    return "done"


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]

    parser = argparse.ArgumentParser(description="Extract notebooks from registered repositories")
    parser = set_up_argument_parser(parser, script_name)
    args = parser.parse_args()

    consts.VERBOSE = args.verbose
    status = None

    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    with connect() as session, savepid():
        apply(
            session=SafeSession(session, interrupted=NB_STOPPED),
            status=status,
            selected_repositories=args.repositories,
            retry=True if args.retry_errors else False,
            count=args.count,
            interval=args.interval,
            reverse=args.reverse,
            check=set(args.check),
            process_repository=process_repository,
            model_type='notebooks/cells'
        )


if __name__ == "__main__":
    main()
