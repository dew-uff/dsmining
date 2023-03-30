import os
import sys
import tarfile
import src.consts as consts

from src.config.states import REP_UNAVAILABLE_FILES
from src.helpers.h3_utils import vprint, to_unicode, unzip_repository, get_pyexec
from src.classes.c4_local_checkers import CompressedLocalChecker, PathLocalChecker


def load_archives(session, repository):

    if repository.zip_path.exists():
        vprint(1, 'Unzipping repository')

        try:
            msg = unzip_repository(repository)
            if msg != "done":
                vprint(2, "repository not found")
                raise Exception("Extraction failure. Fallback")

        except Exception as err:
            vprint(1, 'Failed: {}'.format(err))
            try:
                tarzip = tarfile.open(str(repository.zip_path))
            except Exception as err:  # pylint: disable=broad-except
                vprint(1, err)
                return True, None
            zip_path = to_unicode(repository.hash_dir2)
            return False, (tarzip, zip_path)

    if repository.path.exists():
        repo_path = to_unicode(repository.path)
        return False, (None, repo_path)
    else:
        repository.state = REP_UNAVAILABLE_FILES
        session.add(repository)
        vprint(1, "Failed to load repository. Skipping")
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

    vprint(1, 'Loading file: {}'.format(file))
    name = to_unicode(file.name)

    tarzip, repo_path = archives
    file_path = os.path.join(repo_path, name)

    try:

        if tarzip:
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
    session, cell, dispatches, repository,
    skip_repo, skip_notebook, notebook_id, archives, checker
):
    if notebook_id != cell.notebook_id:
        notebook = cell.notebook_obj

        if not notebook.compatible_version:
            pyexec = get_pyexec(notebook.py_version, consts.VERSIONS)
            if sys.executable != pyexec:
                dispatches.add((notebook.id, pyexec))
                return skip_repo, True, cell.notebook_id, archives, None

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

        vprint(0, 'Loading repository: {}'.format(repository))
        return False, file.repository_id, repository, "todo"

    return skip_repo, repository_id, repository, archives
