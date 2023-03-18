import sys
import os



from src.classes.c2_local_checkers import PathLocalChecker, SetLocalChecker, CompressedLocalChecker

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.consts as consts
from src.db.database import Repository
from src.helpers.h1_utils import SafeSession, to_unicode
from tests.database_config import connection, session
from tests.factories.models import RepositoryFactory, CodeCellFactory, NotebookFactory, PythonFileFactory
from src.helpers.h3_script_helpers import filter_repositories, load_repository, load_notebook, load_files
import src.helpers.h3_script_helpers as h3

class TestH3ScripHelpersFilterRepositories:

    def test_filter_all(self, session):
        rep1, rep2 = RepositoryFactory(session).create_batch(2)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session = SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories = True,
            skip_if_error=consts.R_N_ERROR,
            count = False,
            interval = None,
            reverse=False,
            skip_already_processed = consts.R_N_EXTRACTION
        )

        assert query.count() == 2
        assert rep1 in query.all()
        assert rep2 in query.all()

    def test_filter_count(self, session, capsys):
        RepositoryFactory(session).create_batch(3)

        assert len(session.query(Repository).all()) == 3

        filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=True,
            interval=None,
            reverse=False,
            skip_already_processed = consts.R_N_EXTRACTION
        )

        captured = capsys.readouterr()
        assert captured.out == "3\n"

    def test_filter_reverse(self, session):
        rep1, rep2 = RepositoryFactory(session).create_batch(2)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=None,
            reverse=True,
            skip_already_processed = consts.R_N_EXTRACTION
        )

        assert query.count() == 2
        assert rep1 is query[1]
        assert rep2 is query[0]

    def test_filter_inteval(self, session):
        reps = RepositoryFactory(session).create_batch(10)

        assert len(session.query(Repository).all()) == 10

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=[3,6],
            reverse=False,
            skip_already_processed=consts.R_N_EXTRACTION
        )

        assert query.count() == 4
        assert reps[0], reps[1] not in query.all()
        assert reps[2], reps[3] in query.all()
        assert reps[4], reps[5] in query.all()
        assert reps[6], reps[7] not in query.all()
        assert reps[8], reps[9] not in query.all()

    def test_filter_selected_repositories_30in30(self, session):
        RepositoryFactory(session).create_batch(40)

        assert len(session.query(Repository).all()) == 40

        selected_repositories, query = filter_repositories(
            session = SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                     11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                                     21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                                     31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
            skip_if_error=consts.R_N_ERROR,
            count = False,
            interval = None,
            reverse=False,
            skip_already_processed = consts.R_N_EXTRACTION
        )

        assert selected_repositories == [31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
        assert query.count() == 30

        new_selected_repositories, new_query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=selected_repositories,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=None,
            reverse=False,
            skip_already_processed=consts.R_N_EXTRACTION
        )

        assert new_selected_repositories ==[]
        assert new_query.count() == 10

    def test_filter_filters_skip_if_error(self,session):
        rep = RepositoryFactory(session).create()
        rep_erro = RepositoryFactory(session).create(processed=consts.R_N_ERROR)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=None,
            reverse=False,
            skip_already_processed=consts.R_N_EXTRACTION
        )

        assert query.count() == 1
        assert rep_erro not in query
        assert rep in query

    def test_filter_filters_skip_already_processed(self,session):
        rep = RepositoryFactory(session).create()
        rep_processed = RepositoryFactory(session).create(processed=consts.R_N_EXTRACTION)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=None,
            reverse=False,
            skip_already_processed=consts.R_N_EXTRACTION
        )

        assert query.count() == 1
        assert rep_processed not in query
        assert rep in query


class TestH3ScriptHelpersLoadRepository:
    def test_load_repository_notebook_first_success(self, session, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)
        cell = CodeCellFactory(safe_session).create(repository_id=repository.id, notebook_id = notebook.id)
        initial_repo = repository

        skip_repo = False
        repository_id = None
        repository = None
        archives = None

        skip_repo, repository_id, repository, archives = load_repository(
            safe_session, cell, skip_repo, repository_id, repository, archives
        )
        captured = capsys.readouterr()

        assert skip_repo == False
        assert repository_id == cell.repository_id == repository.id
        assert initial_repo == repository
        assert archives == 'todo'
        assert "Processing repository" in captured.out

    def test_load_repository_notebook_success(self, session, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)
        cell = CodeCellFactory(safe_session).create(repository_id=repository.id, notebook_id = notebook.id)
        initial_repo = repository

        skip_repo = False
        repository_id = repository.id
        path = to_unicode(repository.path)
        archives = (None, path)

        skip_repo, repository_id, repository, archives = load_repository(
            safe_session, cell, skip_repo, repository_id, repository, archives
        )
        captured = capsys.readouterr()


        assert skip_repo == False
        assert repository_id == cell.repository_id == repository.id
        assert initial_repo == repository
        assert archives == (None, path)
        assert captured.out == ""

    def test_load_repository_notebook_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)
        cell = CodeCellFactory(safe_session).create(repository_id=repository.id, notebook_id=notebook.id)
        initial_repo = repository

        skip_repo = False
        repository_id = None
        repository = None
        archives = None

        monkeypatch.setattr(safe_session, 'commit', lambda: (None, 'error 1'))

        skip_repo, repository_id, repository, archives = load_repository(
            safe_session, cell, skip_repo, repository_id, repository, archives
        )
        captured = capsys.readouterr()

        assert skip_repo == False
        assert repository_id == cell.repository_id == repository.id
        assert initial_repo == repository
        assert archives == 'todo'
        assert "Failed to save files from repository" in captured.out

    def test_load_repository_python_file_first_success(self, session, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        python_file = PythonFileFactory(safe_session).create(repository_id=repository.id)
        initial_repo = repository

        skip_repo = False
        repository_id = None
        repository = None
        archives = None

        skip_repo, repository_id, repository, archives = load_repository(
            safe_session, python_file, skip_repo, repository_id, repository, archives
        )
        captured = capsys.readouterr()

        assert skip_repo == False
        assert repository_id == python_file.repository_id == repository.id
        assert initial_repo == repository
        assert archives == 'todo'
        assert "Processing repository" in captured.out

    def test_load_repository_python_file_success(self, session, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        python_file = PythonFileFactory(safe_session).create(repository_id=repository.id)
        initial_repo = repository

        skip_repo = False
        repository_id = repository.id
        path = to_unicode(repository.path)
        archives = (None, path)

        skip_repo, repository_id, repository, archives = load_repository(
            safe_session, python_file, skip_repo, repository_id, repository, archives
        )
        captured = capsys.readouterr()

        assert skip_repo == False
        assert repository_id == python_file.repository_id == repository.id
        assert initial_repo == repository
        assert archives == (None, path)
        assert captured.out == ""


class TestH3ScriptHelpersLoadNotebook:
    def test_load_notebook_first_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)
        cell = CodeCellFactory(safe_session).create(repository_id=repository.id, notebook_id=notebook.id)
        initial_notebook_id = notebook.id

        skip_repo = False
        skip_notebook = False
        notebook_id = None
        path = to_unicode(repository.path)
        archives = (None, path)
        checker = PathLocalChecker(path)

        def mock_load_files(_session, _notebook, _repository,
                            _skip_repo, _skip_notebook, _archives, _checker):
            return False, False, notebook.id, archives, checker


        monkeypatch.setattr(h3, 'load_files', mock_load_files)

        result_skip_repo, result_skip_notebook, \
            result_notebook_id, result_archives, result_checker = load_notebook(
            safe_session, cell, repository, skip_repo, skip_notebook,
            notebook_id, archives, checker
        )

        assert result_skip_repo == False
        assert result_skip_notebook == False
        assert result_notebook_id == initial_notebook_id
        assert result_archives ==  archives
        assert result_checker == checker

    def test_load_notebook_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)
        cell = CodeCellFactory(safe_session).create(repository_id=repository.id, notebook_id=notebook.id)

        skip_repo = False
        skip_notebook = False
        notebook_id = notebook.id
        path = to_unicode(repository.path)
        archives = (None, path)
        checker = PathLocalChecker(path)

        def mock_load_files(_session, _notebook, _repository,
                            _skip_repo, _skip_notebook, _archives, _checker):
            return False, False, notebook.id, archives, checker


        monkeypatch.setattr(h3, 'load_files', mock_load_files)

        result_skip_repo, result_skip_notebook, \
            result_notebook_id, result_archives, result_checker = load_notebook(
            safe_session, cell, repository, skip_repo, skip_notebook,
            notebook_id, archives, checker
        )

        assert result_skip_repo == False
        assert result_skip_notebook == False
        assert result_notebook_id == notebook_id
        assert result_archives ==  archives
        assert result_checker == checker


class TestH3ScriptHelpersLoadFile:
    def test_load_file_notebook_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None
        repo_path = to_unicode(repository.path)

        monkeypatch.setattr(h3, 'load_archives',
                            lambda _session, _repository: (False, (None, repo_path)))
        monkeypatch.setattr(PathLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo == False
        assert skip_notebook == False
        assert notebook_id == notebook.id
        assert archives == (None, repo_path)
        assert isinstance(checker, PathLocalChecker)
        assert checker.base == repo_path


    def test_load_file_notebook_skip_repo(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None

        monkeypatch.setattr(h3, 'load_archives',
                            lambda _session, _repository: (True, None))

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo == True
        assert skip_notebook == False
        assert archives is None
        assert checker is None


    def test_load_file_notebook_no_archives(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None

        monkeypatch.setattr(h3, 'load_archives',
                            lambda _session, _repository: (False, None))


        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo == True
        assert skip_notebook == True
        assert notebook_id == notebook.id
        assert archives is None
        assert checker is None


    def test_load_file_notebook_set_tarzip_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None
        repo_path = to_unicode(repository.path)
        tarzip = ['path1', 'path2']

        monkeypatch.setattr(h3, 'load_archives',
                            lambda _session, _repository: (False, (set(tarzip), repo_path)))
        monkeypatch.setattr(SetLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo == False
        assert skip_notebook == False
        assert notebook_id == notebook.id
        assert archives == (set(tarzip), repo_path)
        assert isinstance(checker, SetLocalChecker)
        assert checker.base == repo_path


    def test_load_file_notebook_tarzip_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None
        repo_path = to_unicode(repository.path)

        monkeypatch.setattr(h3, 'load_archives',
                            lambda _session, _repository: (False, ('test.tar.gz', repo_path)))
        monkeypatch.setattr(CompressedLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo == False
        assert skip_notebook == False
        assert notebook_id == notebook.id
        assert archives == ('test.tar.gz', repo_path)
        assert isinstance(checker, CompressedLocalChecker)
        assert checker.base == repo_path


    def test_load_file_notebook_not_exist_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None
        repo_path = to_unicode(repository.path)

        monkeypatch.setattr(h3, 'load_archives',
                            lambda _session, _repository: (False, (None, repo_path)))
        monkeypatch.setattr(PathLocalChecker, 'exists',
                            lambda _path, _other: False)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)
        captured = capsys.readouterr()

        assert "Repository content problem. File not found" in captured.out
        assert skip_repo == False
        assert skip_notebook == True
        assert notebook_id == notebook.id
        assert archives == (None, repo_path)
        assert isinstance(checker, PathLocalChecker)
        assert checker.base == repo_path


    def test_load_file_python_file_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        python_file = PythonFileFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_python_file = False
        archives = "todo"
        checker = None
        repo_path = to_unicode(repository.path)

        monkeypatch.setattr(h3, 'load_archives',
                            lambda _session, _repository: (False, (None, repo_path)))
        monkeypatch.setattr(PathLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_python_file, python_file_id, archives, checker = \
            load_files(session, python_file, repository, skip_repo, skip_python_file, archives, checker)

        assert skip_repo == False
        assert skip_python_file == False
        assert python_file_id == python_file.id
        assert archives == (None, repo_path)
        assert isinstance(checker, PathLocalChecker)
        assert checker.base == repo_path
