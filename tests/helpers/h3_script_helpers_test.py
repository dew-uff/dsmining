import os
import sys

import src.helpers.h3_utils
import src.helpers.h5_loaders

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import ast
import pytest
import tarfile
import src.consts as consts
import src.extras.e8_extract_files as e8
import src.helpers.h5_loaders as h5

from src.config import Path
from src.classes.c4_local_checkers import PathLocalChecker, SetLocalChecker, CompressedLocalChecker
from src.db.database import Repository, RepositoryFile
from src.helpers.h3_utils import to_unicode, extract_features
from src.classes.c1_safe_session import SafeSession
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory, CodeCellFactory, NotebookFactory, PythonFileFactory
from src.helpers.h5_loaders import load_files, load_notebook, load_repository
from src.helpers.h4_filters import filter_repositories
from src.states import *


class TestH3ScripHelpersFilterRepositories:

    def test_filter_all(self, session):
        rep1, rep2 = RepositoryFactory(session).create_batch(2)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=True,
            count=False,
            interval=None,
            reverse=False,
        )

        assert query.count() == 2
        assert rep1 in query.all()
        assert rep2 in query.all()

    def test_filter_count(self, session, capsys):
        RepositoryFactory(session).create_batch(3)

        assert len(session.query(Repository).all()) == 3

        filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=True,
            count=True,
            interval=None,
            reverse=False
        )

        captured = capsys.readouterr()
        assert captured.out == "3\n"

    def test_filter_reverse(self, session):
        rep1, rep2 = RepositoryFactory(session).create_batch(2)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=True,
            count=False,
            interval=None,
            reverse=True
        )

        assert query.count() == 2
        assert rep1 is query[1]
        assert rep2 is query[0]

    def test_filter_interval(self, session):
        reps = RepositoryFactory(session).create_batch(10)

        assert len(session.query(Repository).all()) == 10

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=True,
            count=False,
            interval=[3, 6],
            reverse=False
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
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                   11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                                   21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                                   31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
            count=False,
            interval=None,
            reverse=False
        )

        assert selected_repositories == [31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
        assert query.count() == 30

        new_selected_repositories, new_query = filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=selected_repositories,
            count=False,
            interval=None,
            reverse=False,
        )

        assert new_selected_repositories == []
        assert new_query.count() == 10


class TestH3ScriptHelpersLoadRepository:
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
        assert "Processing repository" in captured.out

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

        assert skip_repo is False
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

        monkeypatch.setattr(h5, 'load_files', mock_load_files)

        result_skip_repo, result_skip_notebook, \
            result_notebook_id, result_archives, result_checker = \
            load_notebook(
                safe_session, cell, repository, skip_repo, skip_notebook,
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

        def mock_load_files(_session, _notebook, _repository,
                            _skip_repo, _skip_notebook, _archives, _checker):
            return False, False, notebook.id, archives, checker

        monkeypatch.setattr(h5, 'load_files', mock_load_files)

        result_skip_repo, result_skip_notebook, \
            result_notebook_id, result_archives, result_checker = load_notebook(
                safe_session, cell, repository, skip_repo, skip_notebook,
                notebook_id, archives, checker
            )

        assert result_skip_repo is False
        assert result_skip_notebook is False
        assert result_notebook_id == notebook_id
        assert result_archives == archives
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

        monkeypatch.setattr(h5, 'load_archives',
                            lambda _session, _repository: (False, (set(tarzip), repo_path)))
        monkeypatch.setattr(SetLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo is False
        assert skip_notebook is False
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

        monkeypatch.setattr(h5, 'load_archives',
                            lambda _session, _repository: (False, ('test.tar.gz', repo_path)))
        monkeypatch.setattr(CompressedLocalChecker, 'exists',
                            lambda _path, _other: True)

        skip_repo, skip_notebook, notebook_id, archives, checker = \
            load_files(session, notebook, repository, skip_repo, skip_notebook, archives, checker)

        assert skip_repo is False
        assert skip_notebook is False
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


class TestH3ScriptHelpersLoadArchives:
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

    def test_load_archives_set_zip_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()

        def mock_exists(path):
            return str(path) == str(repository.zip_path)

        def mock_process(session_, repository_, skip_if_error=0):   # noqa: F841
            rf = RepositoryFile(repository_id=repository.id,
                                path=str(repository.path))
            safe_session.add(rf)
            safe_session.commit()
            return "done"

        monkeypatch.setattr(Path, 'exists', mock_exists)
        monkeypatch.setattr(e8, 'process_repository', mock_process)

        skip_repo, archives = h5.load_archives(session, repository)
        tarzip, zip_path = archives

        assert skip_repo is False
        assert str(repository.path) in tarzip
        assert zip_path == ""

    def test_load_archives_set_zip_error(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()

        def mock_exists(path):
            return str(path) == str(repository.zip_path)

        def mock_process(session_, repository_, skip_if_error=0):  # noqa: F841
            return "done"

        monkeypatch.setattr(Path, 'exists', mock_exists)
        monkeypatch.setattr(e8, 'process_repository', mock_process)

        skip_repo, archives = h5.load_archives(session, repository)

        assert skip_repo is True
        assert archives is None

    def test_load_archives_zip_success(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create(processed=consts.R_COMPRESS_ERROR)

        def mock_exists(path):
            return str(path) == str(repository.zip_path)

        def mock_process(session_, repository_, skip_if_error=0):  # noqa: F841
            return "error"

        monkeypatch.setattr(Path, 'exists', mock_exists)
        monkeypatch.setattr(e8, 'process_repository', mock_process)
        monkeypatch.setattr(tarfile, 'open', lambda path: "Ok")

        skip_repo, archives = h5.load_archives(session, repository)
        tarzip, zip_path = archives

        assert skip_repo is False
        assert tarzip == 'Ok'
        assert zip_path == to_unicode(repository.hash_dir2)

    def test_load_archives_zip_error(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create(processed=consts.R_COMPRESS_ERROR)

        def mock_exists(path):
            return str(path) == str(repository.zip_path)

        def mock_process(session_, repository_, skip_if_error=0):  # noqa: F841
            return "error"

        def mock_open(path):  # noqa: F841
            raise tarfile.ReadError()

        monkeypatch.setattr(Path, 'exists', mock_exists)
        monkeypatch.setattr(e8, 'process_repository', mock_process)
        monkeypatch.setattr(tarfile, 'open', mock_open)

        skip_repo, archives = h5.load_archives(session, repository)

        assert skip_repo is True
        assert archives is None
        assert repository.processed == consts.R_COMPRESS_ERROR

    def test_load_archives_path_error(self, session, monkeypatch):
        safe_session = SafeSession(session)
        repository = RepositoryFactory(safe_session).create()

        def mock_exists(path):  # noqa: F841
            return False

        monkeypatch.setattr(Path, 'exists', mock_exists)

        skip_repo, archives = h5.load_archives(session, repository)
        assert skip_repo is True
        assert archives is None
        assert repository.processed == consts.R_UNAVAILABLE_FILES


class TestH3ScriptHelpersExtractFeatures:
    def test_extract_features(self, session):
        text = "import pandas as pd\ndf=pd.read_excel('data.xlsx')"
        checker = PathLocalChecker("")
        modules, data_ios = extract_features(text, checker)

        assert modules[0] == (1, "import", "pandas", False)
        assert data_ios[0] == (2, 'input', 'pd', 'read_excel', 'Attribute', "'data.xlsx'", 'Constant')

    def test_extract_features_error(self, session, monkeypatch):
        text = "import pandas as pd\ndf=pd.read_excel('data.xlsx')"
        checker = PathLocalChecker("")

        def mock_parse(text_): raise ValueError  # noqa: F841

        monkeypatch.setattr(ast, 'parse', mock_parse)

        with pytest.raises(SyntaxError):
            extract_features(text, checker)
