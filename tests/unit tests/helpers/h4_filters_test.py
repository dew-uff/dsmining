from src.classes.c1_safe_session import SafeSession
from src.db.database import Repository, Cell, PythonFile
from src.helpers.h4_filters import filter_repositories, filter_markdown_cells
from src.helpers.h4_filters import filter_code_cells, filter_python_files
from src.config.states import NB_STOPPED, PF_EMPTY
from tests.factories.models import RepositoryFactory, MarkdownCellFactory
from tests.factories.models import CodeCellFactory, NotebookFactory, PythonFileFactory
from tests.database_config import connection, session  # noqa: F401


class TestFilterRepositories:

    def test_filter_all(self, session):
        rep1, rep2 = RepositoryFactory(session).create_batch(2)

        assert len(session.query(Repository).all()) == 2

        query = filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=None,
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
            selected_repositories=None,
            count=True,
            interval=None,
            reverse=False
        )

        captured = capsys.readouterr()
        assert captured.out == "3\n"

    def test_filter_reverse(self, session):
        rep1, rep2 = RepositoryFactory(session).create_batch(2)

        assert len(session.query(Repository).all()) == 2

        query = filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=None,
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

        query = filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=None,
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

    def test_filter_selected_repositories(self, session):
        RepositoryFactory(session).create_batch(20)

        assert len(session.query(Repository).all()) == 20

        query = filter_repositories(
            session=SafeSession(session, interrupted=NB_STOPPED),
            selected_repositories=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            count=False,
            interval=None,
            reverse=False
        )

        assert query.count() == 10
        assert session.query(Repository).filter(Repository.id > 10) not in query


class TestFilterMarkdownCells:

    def test_filter_all(self, session):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell1, cell2 = MarkdownCellFactory(session).create_batch(2,
                                                                 repository_id=repository.id,
                                                                 notebook_id=notebook.id)
        code_cell = CodeCellFactory(session).create(repository_id=repository.id,
                                                    notebook_id=notebook.id)

        assert len(session.query(Cell).all()) == 3

        query = filter_markdown_cells(
            session=session,
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=False,
        )

        assert query.count() == 2
        assert cell1 in query.all()
        assert cell2 in query.all()
        assert code_cell not in query.all()

    def test_filter_count(self, session, capsys):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        MarkdownCellFactory(session).create_batch(2, repository_id=repository.id,
                                                  notebook_id=notebook.id)
        CodeCellFactory(session).create(repository_id=repository.id, notebook_id=notebook.id)

        assert len(session.query(Cell).all()) == 3

        filter_markdown_cells(
            session=session,
            selected_repositories=None,
            count=True,
            interval=None,
            reverse=False
        )

        captured = capsys.readouterr()
        assert captured.out == "2\n"

    def test_filter_reverse(self, session):
        repo1, repo2 = RepositoryFactory(session).create_batch(2)
        notebook1 = NotebookFactory(session).create(repository_id=repo1.id)
        notebook2 = NotebookFactory(session).create(repository_id=repo2.id)
        cell1 = MarkdownCellFactory(session).create(repository_id=repo1.id,
                                                    notebook_id=notebook1.id)
        cell2 = MarkdownCellFactory(session).create(repository_id=repo2.id,
                                                    notebook_id=notebook2.id)

        assert len(session.query(Cell).all()) == 2

        query = filter_markdown_cells(
            session=session,
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=True
        )

        assert query.count() == 2
        assert cell1 is query[1]
        assert cell2 is query[0]

    def test_filter_interval(self, session):
        repo1, repo2, repo3 = RepositoryFactory(session).create_batch(3)
        notebook1 = NotebookFactory(session).create(repository_id=repo1.id)
        notebook2 = NotebookFactory(session).create(repository_id=repo2.id)
        notebook3 = NotebookFactory(session).create(repository_id=repo3.id)
        cell1 = MarkdownCellFactory(session).create(repository_id=repo1.id,
                                                    notebook_id=notebook1.id)
        cell2 = MarkdownCellFactory(session).create(repository_id=repo2.id,
                                                    notebook_id=notebook2.id)
        cell3 = MarkdownCellFactory(session).create(repository_id=repo3.id,
                                                    notebook_id=notebook3.id)
        assert len(session.query(Cell).all()) == 3

        query = filter_markdown_cells(
            session=session,
            selected_repositories=None,
            count=False,
            interval=[1, 2],
            reverse=False
        )

        assert query.count() == 2
        assert cell1, cell2 in query.all()
        assert cell3 not in query.all()

    def test_filter_selected_repositories(self, session):
        repo1, repo2, repo3 = RepositoryFactory(session).create_batch(3)
        notebook1 = NotebookFactory(session).create(repository_id=repo1.id)
        notebook2 = NotebookFactory(session).create(repository_id=repo2.id)
        notebook3 = NotebookFactory(session).create(repository_id=repo3.id)
        MarkdownCellFactory(session).create(repository_id=repo1.id,
                                            notebook_id=notebook1.id)
        MarkdownCellFactory(session).create(repository_id=repo2.id,
                                            notebook_id=notebook2.id)
        MarkdownCellFactory(session).create(repository_id=repo3.id,
                                            notebook_id=notebook3.id)

        assert len(session.query(Cell).all()) == 3

        query = filter_markdown_cells(
            session=session,
            selected_repositories=[2],
            count=False,
            interval=None,
            reverse=False
        )

        assert query.count() == 1
        assert session.query(Cell).filter(Cell.id in [1, 3]) not in query


class TestFilterCodeCells:

    def test_filter_all(self, session):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell1, cell2 = CodeCellFactory(session).create_batch(2,
                                                             repository_id=repository.id,
                                                             notebook_id=notebook.id)
        markdown_cell = MarkdownCellFactory(session).create(repository_id=repository.id,
                                                            notebook_id=notebook.id)

        assert len(session.query(Cell).all()) == 3

        query = filter_code_cells(
            session=session,
            selected_notebooks=None,
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=False,
        )

        assert query.count() == 2
        assert cell1 in query.all()
        assert cell2 in query.all()
        assert markdown_cell not in query.all()

    def test_filter_count(self, session, capsys):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        CodeCellFactory(session).create_batch(2, repository_id=repository.id, notebook_id=notebook.id)
        MarkdownCellFactory(session).create(repository_id=repository.id, notebook_id=notebook.id)

        assert len(session.query(Cell).all()) == 3

        filter_code_cells(
            session=session,
            selected_notebooks=None,
            selected_repositories=None,
            count=True,
            interval=None,
            reverse=False
        )

        captured = capsys.readouterr()
        assert captured.out == "2\n"

    def test_filter_reverse(self, session):
        repo1, repo2 = RepositoryFactory(session).create_batch(2)
        notebook1 = NotebookFactory(session).create(repository_id=repo1.id)
        notebook2 = NotebookFactory(session).create(repository_id=repo2.id)
        cell1 = CodeCellFactory(session).create(repository_id=repo1.id,
                                                notebook_id=notebook1.id)
        cell2 = CodeCellFactory(session).create(repository_id=repo2.id,
                                                notebook_id=notebook2.id)

        assert len(session.query(Cell).all()) == 2

        query = filter_code_cells(
            session=session,
            selected_notebooks=None,
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=True
        )

        assert query.count() == 2
        assert cell1 is query[1]
        assert cell2 is query[0]

    def test_filter_interval(self, session):
        repo1, repo2, repo3 = RepositoryFactory(session).create_batch(3)
        notebook1 = NotebookFactory(session).create(repository_id=repo1.id)
        notebook2 = NotebookFactory(session).create(repository_id=repo2.id)
        notebook3 = NotebookFactory(session).create(repository_id=repo3.id)
        cell1 = CodeCellFactory(session).create(repository_id=repo1.id,
                                                notebook_id=notebook1.id)
        cell2 = CodeCellFactory(session).create(repository_id=repo2.id,
                                                notebook_id=notebook2.id)
        cell3 = CodeCellFactory(session).create(repository_id=repo3.id,
                                                notebook_id=notebook3.id)
        assert len(session.query(Cell).all()) == 3

        query = filter_code_cells(
            session=session,
            selected_notebooks=None,
            selected_repositories=None,
            count=False,
            interval=[1, 2],
            reverse=False
        )

        assert query.count() == 2
        assert cell1, cell2 in query.all()
        assert cell3 not in query.all()

    def test_filter_selected_notebooks(self, session):
        repo1 = RepositoryFactory(session).create()
        notebook1 = NotebookFactory(session).create(repository_id=repo1.id)
        notebook2 = NotebookFactory(session).create(repository_id=repo1.id)
        CodeCellFactory(session).create(repository_id=repo1.id, notebook_id=notebook1.id)
        CodeCellFactory(session).create(repository_id=repo1.id, notebook_id=notebook1.id)
        CodeCellFactory(session).create(repository_id=repo1.id, notebook_id=notebook2.id)

        assert len(session.query(Cell).all()) == 3

        query = filter_code_cells(
            session=session,
            selected_notebooks=[2],
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=False
        )

        assert query.count() == 1
        assert query.first().id ==3
        assert session.query(Cell).filter(Cell.id in [1, 2]) not in query

    def test_filter_selected_repositories(self, session):
        repo1, repo2, repo3 = RepositoryFactory(session).create_batch(3)
        notebook1 = NotebookFactory(session).create(repository_id=repo1.id)
        notebook2 = NotebookFactory(session).create(repository_id=repo2.id)
        notebook3 = NotebookFactory(session).create(repository_id=repo3.id)
        CodeCellFactory(session).create(repository_id=repo1.id, notebook_id=notebook1.id)
        CodeCellFactory(session).create(repository_id=repo2.id, notebook_id=notebook2.id)
        CodeCellFactory(session).create(repository_id=repo3.id, notebook_id=notebook3.id)

        assert len(session.query(Cell).all()) == 3

        query = filter_code_cells(
            session=session,
            selected_notebooks=None,
            selected_repositories=[2],
            count=False,
            interval=None,
            reverse=False
        )

        assert query.count() == 1
        assert session.query(Cell).filter(Cell.id in [1, 3]) not in query

    def test_filter_not_python(self, session):
        repository = RepositoryFactory(session).create()
        notebook = NotebookFactory(session).create(repository_id=repository.id)
        cell1 = CodeCellFactory(session).create(repository_id=repository.id,
                                                notebook_id=notebook.id)
        cell2 = CodeCellFactory(session).create(repository_id=repository.id,
                                                notebook_id=notebook.id,
                                                python=0)

        query = filter_code_cells(
            session=session,
            selected_notebooks=None,
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=False,
        )

        assert query.count() == 1
        assert cell1 in query.all()
        assert cell2 not in query.all()


class TestFilterPythonFiles:

    def test_filter_all(self, session):
        repository = RepositoryFactory(session).create()
        pf1, pf2 = PythonFileFactory(session).create_batch(2, repository_id=repository.id)

        assert len(session.query(PythonFile).all()) == 2

        query = filter_python_files(
            session=session,
            selected_python_files=None,
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=False,
        )

        assert query.count() == 2
        assert pf1, pf2 in query.all()

    def test_filter_count(self, session, capsys):
        repository = RepositoryFactory(session).create()
        PythonFileFactory(session).create_batch(2, repository_id=repository.id)

        assert len(session.query(PythonFile).all()) == 2

        filter_python_files(
            session=session,
            selected_python_files=None,
            selected_repositories=None,
            count=True,
            interval=None,
            reverse=False
        )

        captured = capsys.readouterr()
        assert captured.out == "2\n"

    def test_filter_reverse(self, session):
        repo1, repo2 = RepositoryFactory(session).create_batch(2)
        pf1 = PythonFileFactory(session).create(repository_id=repo1.id)
        pf2 = PythonFileFactory(session).create(repository_id=repo2.id)

        assert len(session.query(PythonFile).all()) == 2

        query = filter_python_files(
            session=session,
            selected_python_files=None,
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=True
        )

        assert query.count() == 2
        assert pf1 is query[1]
        assert pf2 is query[0]

    def test_filter_interval(self, session):
        repo1, repo2, repo3 = RepositoryFactory(session).create_batch(3)
        pf1 = PythonFileFactory(session).create(repository_id=repo1.id)
        pf2 = PythonFileFactory(session).create(repository_id=repo2.id)
        pf3 = PythonFileFactory(session).create(repository_id=repo3.id)
        assert len(session.query(PythonFile).all()) == 3

        query = filter_python_files(
            session=session,
            selected_python_files=None,
            selected_repositories=None,
            count=False,
            interval=[1, 2],
            reverse=False
        )

        assert query.count() == 2
        assert pf1, pf2 in query.all()
        assert pf3 not in query.all()

    def test_filter_selected_python_files(self, session):
        repo1 = RepositoryFactory(session).create()
        PythonFileFactory(session).create(repository_id=repo1.id)
        PythonFileFactory(session).create(repository_id=repo1.id)
        PythonFileFactory(session).create(repository_id=repo1.id)

        assert len(session.query(PythonFile).all()) == 3

        query = filter_python_files(
            session=session,
            selected_python_files=[1, 2],
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=False
        )

        assert query.count() == 2
        assert session.query(PythonFile).filter(PythonFile.id == 3) not in query

    def test_filter_selected_repositories(self, session):
        repo1, repo2, repo3 = RepositoryFactory(session).create_batch(3)
        PythonFileFactory(session).create(repository_id=repo1.id)
        PythonFileFactory(session).create(repository_id=repo2.id)
        PythonFileFactory(session).create(repository_id=repo3.id)

        assert len(session.query(PythonFile).all()) == 3

        query = filter_python_files(
            session=session,
            selected_python_files=None,
            selected_repositories=[2],
            count=False,
            interval=None,
            reverse=False
        )

        assert query.count() == 1
        assert session.query(PythonFile).filter(PythonFile.id in [1, 3]) not in query

    def test_filter_empty_file(self, session):
        repository = RepositoryFactory(session).create()
        pf1 = PythonFileFactory(session).create(repository_id=repository.id)
        pf2 = PythonFileFactory(session).create(repository_id=repository.id,
                                                state=PF_EMPTY)

        query = filter_python_files(
            session=session,
            selected_python_files=None,
            selected_repositories=None,
            count=False,
            interval=None,
            reverse=False,
        )

        assert query.count() == 1
        assert pf1 in query.all()
        assert pf2 not in query.all()
