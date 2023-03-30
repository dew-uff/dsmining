import os
import sys
src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import tarfile
import src.helpers.h5_loaders as h5

from src.config.consts import Path
from src.helpers.h3_utils import to_unicode
from src.config.states import REP_UNAVAILABLE_FILES
from tests.stubs.others import stub_unzip
from src.classes.c1_safe_session import SafeSession
from src.helpers.h5_loaders import load_files, load_notebook, load_repository
from src.classes.c4_local_checkers import PathLocalChecker,  CompressedLocalChecker
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory, CodeCellFactory
from tests.factories.models import NotebookFactory, PythonFileFactory


class TestLoadRepository:
    def test_load_repository_notebook_first_success(self, session, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)
        cell = CodeCellFactory(safe_session).create(repository_id=repository.id, notebook_id=notebook.id)
        initial_repo = repository

        skip_repo = False
        repository_id = None
        repository = None
        archives = None

        skip_repo, repository_id, repository, archives = load_repository(
            safe_session, cell, skip_repo, repository_id, repository, archives
        )
        captured = capsys.readouterr()

        assert skip_repo is False
        assert repository_id == cell.repository_id == repository.id
        assert initial_repo == repository
        assert archives == 'todo'
        assert "Loading repository" in captured.out

    def test_load_repository_notebook_success(self, session, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)
        cell = CodeCellFactory(safe_session).create(repository_id=repository.id, notebook_id=notebook.id)
        initial_repo = repository

        skip_repo = False
        repository_id = repository.id
        path = to_unicode(repository.path)
        archives = (None, path)

        skip_repo, repository_id, repository, archives = load_repository(
            safe_session, cell, skip_repo, repository_id, repository, archives
        )
        captured = capsys.readouterr()

        assert skip_repo is False
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

        assert skip_repo is False
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

        assert skip_repo is False
        assert repository_id == python_file.repository_id == repository.id
        assert initial_repo == repository
        assert archives == 'todo'
        assert "Loading repository" in captured.out

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

        assert skip_repo is False
        assert repository_id == python_file.repository_id == repository.id
        assert initial_repo == repository
        assert archives == (None, path)
        assert captured.out == ""


class TestLoadNotebook:
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
        dispatches = set()

        def mock_load_files(_session, _notebook, _repository,
                            _skip_repo, _skip_notebook, _archives, _checker):
            return False, False, notebook.id, archives, checker

        monkeypatch.setattr(h5, 'load_files', mock_load_files)

        result_skip_repo, result_skip_notebook, \
            result_notebook_id, result_archives, result_checker = \
            load_notebook(
                safe_session, cell, dispatches, repository, skip_repo, skip_notebook,
                notebook_id, archives, checker)

        assert result_skip_repo is False
        assert result_skip_notebook is False
        assert result_notebook_id == initial_notebook_id
        assert result_archives == archives
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
        dispatches = set()
        def mock_load_files(_session, _notebook, _repository,
                            _skip_repo, _skip_notebook, _archives, _checker):
            return False, False, notebook.id, archives, checker

        monkeypatch.setattr(h5, 'load_files', mock_load_files)

        result_skip_repo, result_skip_notebook, \
            result_notebook_id, result_archives, result_checker = load_notebook(
                safe_session, cell, dispatches, repository, skip_repo, skip_notebook,
                notebook_id, archives, checker
            )

        assert result_skip_repo is False
        assert result_skip_notebook is False
        assert result_notebook_id == notebook_id
        assert result_archives == archives
        assert result_checker == checker

    def test_load_notebook_not_compatible(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id, language_version="2.7.15")
        cell = CodeCellFactory(safe_session).create(repository_id=repository.id, notebook_id=notebook.id)

        skip_repo = False
        skip_notebook = False
        notebook_id = None
        path = to_unicode(repository.path)
        archives = (None, path)
        checker = PathLocalChecker(path)
        dispatches = set()

        def mock_load_files(_session, _notebook, _repository,
                            _skip_repo, _skip_notebook, _archives, _checker):
            return False, False, notebook.id, archives, checker

        monkeypatch.setattr(h5, 'load_files', mock_load_files)

        result_skip_repo, result_skip_notebook, \
            result_notebook_id, result_archives, result_checker = \
            load_notebook(
                safe_session, cell, dispatches, repository, skip_repo, skip_notebook,
                notebook_id, archives, checker)

        dispatches = list(dispatches)

        assert result_skip_repo is False
        assert result_skip_notebook is True
        assert len(dispatches) == 1
        assert dispatches[0][0] == notebook.id
        assert "dsm27" in dispatches[0][1]


class TestLoadFile:
    def test_load_file_notebook_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None
        repo_path = to_unicode(repository.path)

        monkeypatch.setattr(h5, 'load_archives',
                            lambda _session, _repository: (False, (None, repo_path)))
        monkeypatch.setattr(PathLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo is False
        assert skip_notebook is False
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

        monkeypatch.setattr(h5, 'load_archives',
                            lambda _session, _repository: (True, None))

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo is True
        assert skip_notebook is False
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

        monkeypatch.setattr(h5, 'load_archives',
                            lambda _session, _repository: (False, None))

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo is True
        assert skip_notebook is True
        assert notebook_id == notebook.id
        assert archives is None
        assert checker is None

    def test_load_file_notebook_tarzip_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None
        zip_path = to_unicode(repository.hash_dir2)

        monkeypatch.setattr(h5, 'load_archives',
                            lambda _session, _repository: (False, ('test.tar.gz', zip_path)))
        monkeypatch.setattr(CompressedLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo is False
        assert skip_notebook is False
        assert notebook_id == notebook.id
        assert archives == ('test.tar.gz', zip_path)
        assert isinstance(checker, CompressedLocalChecker)
        assert checker.base == zip_path

    def test_load_file_notebook_not_exist_error(self, session, monkeypatch, capsys):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()
        notebook = NotebookFactory(safe_session).create(repository_id=repository.id)

        skip_repo = False
        skip_notebook = False
        archives = "todo"
        checker = None
        repo_path = to_unicode(repository.path)

        monkeypatch.setattr(h5, 'load_archives',
                            lambda _session, _repository: (False, (None, repo_path)))
        monkeypatch.setattr(PathLocalChecker, 'exists',
                            lambda _path, _other: False)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)
        captured = capsys.readouterr()

        assert "Repository content problem. File not found" in captured.out
        assert skip_repo is False
        assert skip_notebook is True
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

        monkeypatch.setattr(h5, 'load_archives',
                            lambda _session, _repository: (False, (None, repo_path)))
        monkeypatch.setattr(PathLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_python_file, python_file_id, archives, checker = \
            load_files(session, python_file, repository, skip_repo, skip_python_file, archives, checker)

        assert skip_repo is False
        assert skip_python_file is False
        assert python_file_id == python_file.id
        assert archives == (None, repo_path)
        assert isinstance(checker, PathLocalChecker)
        assert checker.base == repo_path


class TestLoadArchives:
    def test_load_archives_path_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()

        def mock_exists(path):
            return not str(path) == str(repository.zip_path)

        monkeypatch.setattr(Path, 'exists', mock_exists)

        skip_repo, archives = h5.load_archives(session, repository)
        tarzip, repo_path = archives

        assert skip_repo is False
        assert tarzip is None
        assert repo_path == to_unicode(repository.path)

    def test_load_archives_zip_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()

        def mock_exists(path):
            return str(path) == str(repository.zip_path)

        monkeypatch.setattr(Path, 'exists', mock_exists)
        monkeypatch.setattr(tarfile, 'open', lambda path: "Ok")
        monkeypatch.setattr(h5, 'unzip_repository', stub_unzip)
        monkeypatch.setattr(Path, 'exists', lambda path: True)

        skip_repo, archives = h5.load_archives(session, repository)
        tarzip, repo_path = archives

        assert skip_repo is False
        assert tarzip is None
        assert repo_path == to_unicode(repository.path)

    def test_load_archives_error_zip_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()

        def mock_exists(path):
            return str(path) == str(repository.zip_path)

        monkeypatch.setattr(Path, 'exists', mock_exists)
        monkeypatch.setattr(tarfile, 'open', lambda path: "Ok")

        skip_repo, archives = h5.load_archives(session, repository)
        tarzip, zip_path = archives

        assert skip_repo is False
        assert tarzip == 'Ok'
        assert zip_path == to_unicode(repository.hash_dir2)

    def test_load_archives_error_zip_error(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()

        def mock_exists(path):
            return str(path) == str(repository.zip_path)

        def mock_open(path):  # noqa: F841
            raise tarfile.ReadError()

        monkeypatch.setattr(Path, 'exists', mock_exists)
        monkeypatch.setattr(tarfile, 'open', mock_open)

        skip_repo, archives = h5.load_archives(session, repository)

        assert skip_repo is True
        assert archives is None

    def test_load_archives_path_error(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()

        def mock_exists(path):  # noqa: F841
            return False

        monkeypatch.setattr(Path, 'exists', mock_exists)

        skip_repo, archives = h5.load_archives(session, repository)
        assert skip_repo is True
        assert archives is None
        assert repository.state == REP_UNAVAILABLE_FILES
