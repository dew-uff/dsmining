"""Load markdown features"""
import argparse
import os
import sys
import ast
import tarfile
import config
import consts

from itertools import groupby
from src.db.database import Cell, CellFeature, CellModule, CellName, CodeAnalysis, connect
from src.db.database import RepositoryFile
from h1_utils import vprint, StatusLogger, check_exit, savepid, to_unicode
from h1_utils import get_pyexec, invoke, timeout, TimeoutError, SafeSession
from h1_utils import mount_basedir
from future.utils.surrogateescape import register_surrogateescape
from e5_extract_files import process_repository
from h4_ast_classes import PathLocalChecker, SetLocalChecker
from h4_ast_classes import CompressedLocalChecker, CellVisitor


@timeout(1 * 60, use_signals=False)
def extract_features(text, checker):
    """Use cell visitor to extract features from cell text"""
    visitor = CellVisitor(checker)
    try:
        parsed = ast.parse(text)
    except ValueError:
        raise SyntaxError("Invalid escape")
    visitor.visit(parsed)
    visitor.counter["ast_others"] = visitor.counter["ast_others"].strip()
    return (
        visitor.counter,
        visitor.modules,
        visitor.ipython_features,
        visitor.names
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
            session.query(CellFeature).filter(
                CellFeature.cell_id == cell.id
            ).delete()
            + session.query(CellModule).filter(
                CellModule.cell_id == cell.id
            ).delete()
            + session.query(CellName).filter(
                CellName.cell_id == cell.id
            ).delete()
            + session.query(CodeAnalysis).filter(
                CodeAnalysis.cell_id == cell.id
            ).delete()
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
        try:
            vprint(2, "Extracting features")
            analysis, modules, features, names = extract_features(cell.source, checker)
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
            analysis = {
                x.name: 0 for x in CodeAnalysis.__table__.columns
                if x.name not in {"id", "repository_id", "notebook_id", "cell_id", "index"}
            }
            analysis["ast_others"] = ""
            modules = []
            features = []
            names = {}
        else:
            vprint(3, "Ok")

        analysis["processed"] = processed

        code_analysis = CodeAnalysis(
            repository_id=repository_id,
            notebook_id=notebook_id,
            cell_id=cell.id,
            index=cell.index,
            **analysis
        )
        dependents = []
        for line, import_type, module_name, local in modules:
            dependents.append(CellModule(
                repository_id=repository_id,
                notebook_id=notebook_id,
                cell_id=cell.id,
                index=cell.index,

                line=line,
                import_type=import_type,
                module_name=module_name,
                local=local,
            ))

        for line, column, feature_name, feature_value in features:
            dependents.append(CellFeature(
                repository_id=repository_id,
                notebook_id=notebook_id,
                cell_id=cell.id,
                index=cell.index,

                line=line,
                column=column,
                feature_name="IPython/" + feature_name,
                feature_value=feature_value,
            ))

        for (scope, context), values in names.items():
            for name, count in values.items():
                dependents.append(CellName(
                    repository_id=repository_id,
                    notebook_id=notebook_id,
                    cell_id=cell.id,
                    index=cell.index,

                    scope=scope,
                    context=context,
                    name=name,
                    count=count,
                ))
        vprint(2, "Adding session objects")
        session.dependent_add(
            code_analysis, dependents, "analysis_id"
        )
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
        if not notebook.compatible_version:
            pyexec = get_pyexec(notebook.py_version, config.VERSIONS)
            if sys.executable != pyexec:
                dispatches.add((notebook.id, pyexec))
                return skip_repo, True, cell.notebook_id, archives, None

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
    """Extract code cell features"""
    while selected_notebooks:
        filters = [
            Cell.processed.op('&')(consts.C_PROCESS_OK) == 0,
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


def pos_apply(dispatches, retry_errors, retry_timeout, verbose):
    """Dispatch execution to other python versions"""
    key = lambda x: x[1]
    dispatches = sorted(list(dispatches), key=key)
    for pyexec, disp in groupby(dispatches, key=key):
        vprint(0, "Dispatching to {}".format(pyexec))
        extra = []
        if retry_errors:
            extra.append("-e")
        if retry_timeout:
            extra.append("-t")
        extra.append("-n")

        notebook_ids = [x[0] for x in disp]
        while notebook_ids:
            ids = notebook_ids[:20000]
            args = extra + ids
            invoke(pyexec, "-u", __file__, "-v", verbose, *args)
            notebook_ids = notebook_ids[20000:]


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

        # pos_apply(
        #     dispatches,
        #     args.retry_errors,
        #     args.retry_timeout,
        #     args.verbose
        # )


if __name__ == '__main__':
    main()
