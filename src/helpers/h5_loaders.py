import os
import tarfile


from src.classes.c4_local_checkers import SetLocalChecker, CompressedLocalChecker, PathLocalChecker
from src.db.database import RepositoryFile
from src.extras import e8_extract_files as e8
from src.helpers.h3_utils import vprint, to_unicode
from src.states import REP_UNAVAILABLE_FILES


def load_archives(session, repository):

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
            except tarfile.ReadError:
                return True, None
            zip_path = to_unicode(repository.hash_dir2)
            return False, (tarzip, zip_path)

    elif repository.path.exists():
        repo_path = to_unicode(repository.path)
        return False, (None, repo_path)
    else:
        repository.state = REP_UNAVAILABLE_FILES
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
