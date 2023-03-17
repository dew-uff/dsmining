"""Load markdown features"""
import argparse
import os
import ast
import tarfile
import src.config as config
import src.consts as consts

from src.db.database import CellModule, connect, CellDataIO
from src.db.database import RepositoryFile
from src.helpers.h1_utils import vprint, StatusLogger, check_exit, savepid, to_unicode
from src.helpers.h1_utils import TimeoutError, SafeSession
from src.helpers.h1_utils import mount_basedir
from future.utils.surrogateescape import register_surrogateescape
from e8_extract_files import process_repository
from src.classes.c2_local_checkers import PathLocalChecker, SetLocalChecker, CompressedLocalChecker
from src.classes.c3_cell_visitor import  CellVisitor
from src.helpers.h3_script_helpers import filter_code_cells


# @timeout(1 * 60, use_signals=False)
def extract_features(text, checker):
    """Use cell visitor to extract features from cell text"""
    visitor = CellVisitor(checker)
    try:
        parsed = ast.parse(text)
    except ValueError:
        raise SyntaxError("Invalid escape")
    visitor.visit(parsed)
    return (
        visitor.modules,
        visitor.data_ios
    )


def process_code_cell(
    session, repository_id, notebook_id, cell, checker,
    skip_if_error=consts.C_PROCESS_ERROR,
    skip_if_syntaxerror=consts.C_SYNTAX_ERROR,
    skip_if_timeout=consts.C_TIMEOUT,
):
    """Process Markdown Cell to collect features"""
    if cell.processed & consts.C_PROCESS_OK:
        return 'already processed'

    retry = False
    retry |= not skip_if_error and cell.processed & consts.C_PROCESS_ERROR
    retry |= not skip_if_syntaxerror and cell.processed & consts.C_SYNTAX_ERROR
    retry |= not skip_if_timeout and cell.processed & consts.C_TIMEOUT

    if retry:
        deleted = (
            session.query(CellModule).filter(
                CellModule.cell_id == cell.id
            ).delete()
            # + session.query(CodeAnalysis).filter(
            #     CodeAnalysis.cell_id == cell.id
            # ).delete()
        )
        if deleted:
            vprint(2, "Deleted {} rows".format(deleted))
        if cell.processed & consts.C_PROCESS_ERROR:
            cell.processed -= consts.C_PROCESS_ERROR
        if cell.processed & consts.C_SYNTAX_ERROR:
            cell.processed -= consts.C_SYNTAX_ERROR
        if cell.processed & consts.C_TIMEOUT:
            cell.processed -= consts.C_TIMEOUT
        session.add(cell)

    try:
        error = False
        modules = None
        data_ios = None
        try:
            vprint(2, "Extracting features")
            modules, data_ios = extract_features(cell.source, checker)
            processed = consts.A_OK
        except TimeoutError:
            processed = consts.A_TIMEOUT
            cell.processed |= consts.C_TIMEOUT
            error = True
        except SyntaxError:
            processed = consts.A_SYNTAX_ERROR
            cell.processed |= consts.C_SYNTAX_ERROR
            error = True
        if error:
            vprint(3, "Failed: {}".format(processed))
            modules = []
            data_ios = []
        else:
            vprint(3, "Ok")

        vprint(2, "Adding session objects")
        for line, import_type, module_name, local in modules:
            session.add(CellModule(
                repository_id=repository_id,
                notebook_id=notebook_id,
                cell_id=cell.id,
                index=cell.index,

                line=line,
                import_type=import_type,
                module_name=module_name,
                local=local,
            ))

        for line, type_, caller,\
                function_name, function_type,\
                source, source_type in data_ios:
            session.add(CellDataIO(
                repository_id=repository_id,
                notebook_id=notebook_id,
                cell_id=cell.id,
                index=cell.index,

                line=line,
                type=type_,
                caller=caller,
                function_name=function_name,
                function_type=function_type,
                source=source,
                source_type=source_type
            ))

        cell.processed |= consts.C_PROCESS_OK
        return "done"
    except Exception as err:
        cell.processed |= consts.C_PROCESS_ERROR
        if config.VERBOSE > 4:
            import traceback
            traceback.print_exc()
        return 'Failed to process ({})'.format(err)
    finally:
        session.add(cell)


def load_archives(session, repository):
    if not repository.processed & consts.R_EXTRACTED_FILES:
        if repository.zip_path.exists():
            vprint(1, 'Extracting files')
            result = process_repository(session, repository, skip_if_error=0)
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


def load_repository(session, cell, skip_repo, repository_id, repository, archives):
    if repository_id != cell.repository_id:
        repository = cell.repository_obj
        success, msg = session.commit()
        if not success:
            vprint(0, 'Failed to save cells from repository {} due to {}'.format(
                repository, msg
            ))

        vprint(0, 'Processing repository: {}'.format(repository))
        return False, cell.repository_id, repository, "todo"

    return skip_repo, repository_id, repository, archives


def load_notebook(
    session, cell, dispatches, repository,
    skip_repo, skip_notebook, notebook_id, archives, checker
):
    if notebook_id != cell.notebook_id:
        notebook_id = cell.notebook_id
        notebook = cell.notebook_obj

        # if not notebook.compatible_version:
        #     pyexec = get_pyexec(notebook.py_version, config.VERSIONS)
        #     if sys.executable != pyexec:
        #         dispatches.add((notebook.id, pyexec))
        #         return skip_repo, True, cell.notebook_id, archives, None

        if archives == "todo":
            skip_repo, archives = load_archives(session, repository)
            if skip_repo:
                return skip_repo, skip_notebook, cell.notebook_id, archives, None
        if archives is None:
            return True, True, cell.notebook_id, archives, None

        vprint(1, 'Processing notebook: {}'.format(notebook))
        name = to_unicode(notebook.name)

        tarzip, repo_path = archives

        notebook_path = os.path.join(repo_path, name)
        try:
            if isinstance(tarzip, set):
                checker = SetLocalChecker(tarzip, notebook_path)
            elif tarzip:
                checker = CompressedLocalChecker(tarzip, notebook_path)
            else:
                checker = PathLocalChecker(notebook_path)
            if not checker.exists(notebook_path):
                raise Exception("Repository content problem. Notebook not found")
            return skip_repo, False, cell.notebook_id, archives, checker
        except Exception as err:
            vprint(2, "Failed to load notebook {} due to {}".format(notebook, err))
            return skip_repo, True, cell.notebook_id, archives, checker
    return skip_repo, skip_notebook, notebook_id, archives, checker


def apply(
    session, status, dispatches, selected_notebooks,
    skip_if_error, skip_if_syntaxerror, skip_if_timeout,
    count, interval, reverse, check
):
    """ Extracts code cells features """
    while selected_notebooks:

        selected_notebooks, query = filter_code_cells\
            (session=session, selected_notebooks=selected_notebooks,
             skip_if_error=skip_if_error, skip_if_syntaxerror=skip_if_syntaxerror,
             skip_if_timeout=skip_if_timeout, count=count, interval=interval,
             reverse=reverse,
             skip_already_processed=consts.C_PROCESS_OK)

        skip_repo = False
        repository_id = None
        repository = None
        archives = None

        skip_notebook = False
        notebook_id = None
        checker = None

        for cell in query:

            if check_exit(check):
                session.commit()
                vprint(0, 'Found .exit file. Exiting')
                return
            status.report()

            with mount_basedir():
                skip_repo, repository_id, repository, archives = load_repository(
                    session, cell, skip_repo, repository_id, repository, archives
                )
                if skip_repo:
                    continue

                skip_repo, skip_notebook, notebook_id, archives, checker = load_notebook(
                    session, cell, dispatches, repository,
                    skip_repo, skip_notebook, notebook_id, archives, checker
                )
                if skip_repo or skip_notebook:
                    continue

                vprint(2, 'Processing cell: {}'.format(cell))
                result = process_code_cell(
                    session, repository_id, notebook_id, cell, checker,
                    skip_if_error, skip_if_syntaxerror, skip_if_timeout,
                )
                vprint(2, result)

            status.count += 1
        session.commit()


def main():
    """Main function"""
    register_surrogateescape()
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(
        description='Execute repositories')
    parser.add_argument('-v', '--verbose', type=int, default=config.VERBOSE,
                        help='increase output verbosity')
    parser.add_argument("-n", "--notebooks", type=int, default=None,
                        nargs="*",
                        help="notebooks ids")
    parser.add_argument('-e', '--retry-errors', action='store_true',
                        help='retry errors')
    parser.add_argument('-s', '--retry-syntaxerrors', action='store_true',
                        help='retry syntax errors')
    parser.add_argument('-t', '--retry-timeout', action='store_true',
                        help='retry timeout')
    parser.add_argument('-i', '--interval', type=int, nargs=2,
                        default=config.REPOSITORY_INTERVAL,
                        help='repository id interval')
    parser.add_argument('-c', '--count', action='store_true',
                        help='count results')
    parser.add_argument('-r', '--reverse', action='store_true',
                        help='iterate in reverse order')
    parser.add_argument('--check', type=str, nargs='*',
                        default={'all', script_name, script_name + '.py'},
                        help='check name in .exit')

    args = parser.parse_args()
    config.VERBOSE = args.verbose
    status = None
    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    dispatches = set()
    with savepid():
        with connect() as session:
            apply(
                SafeSession(session),
                status,
                dispatches,
                args.notebooks or True,
                0 if args.retry_errors else consts.C_PROCESS_ERROR,
                0 if args.retry_syntaxerrors else consts.C_SYNTAX_ERROR,
                0 if args.retry_timeout else consts.C_TIMEOUT,
                args.count,
                args.interval,
                args.reverse,
                set(args.check)
            )


if __name__ == '__main__':
    main()
