from src.db.database import Repository, Notebook, PythonFile, RequirementFile
from src.db.database import Cell, CellMarkdownFeature, CellModule, CellDataIO
from src.db.database import PythonFileModule, PythonFileDataIO, Commit

import factory


def RepositoryFactory(session):
    class _RepositoryFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = Repository
            sqlalchemy_session = session

        domain = "github.com"
        repository = factory.Sequence(lambda n: 'person{}/respository{}'.format(n + 1, n + 1))
        hash_dir1 = "test"
        hash_dir2 = factory.Sequence(lambda n: "test_directory{}".format(n + 1))
        commit = "8a34a4f653bdbdc01415a94dc20d4e9b97438965"
        is_mirror = 0
        disk_usage = 34707
        primary_language = "Jupyter Notebook"

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):  # noqa: F841
            if create:
                session.add(self)
                session.commit()

    return _RepositoryFactory


def CommitFactory(session):
    class _CommitFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = Commit
            sqlalchemy_session = session

        type = "commit"
        hash = factory.Sequence(lambda n: "dd{}d1c3".format(n))
        author = factory.Sequence(lambda n: 'person{}'.format(n + 1))
        message = "test message"

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _CommitFactory


def NotebookFactory(session):
    class _NotebookFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = Notebook
            sqlalchemy_session = session

        name = 'file.ipynb'
        nbformat = '4.0'
        kernel = 'python3'
        language = 'python'
        language_version = '3.5.1'
        max_execution_count = 22
        total_cells = 61
        code_cells = 22
        code_cells_with_output = 15
        markdown_cells = 39
        raw_cells = 0
        unknown_cell_formats = 0
        empty_cells = 0

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _NotebookFactory


def MarkdownCellFactory(session):
    class _CellFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = Cell
            sqlalchemy_session = session

        cell_type = 'markdown'
        execution_count = None
        lines = 2
        output_formats = None
        source = "Recall what these components mean: the full data is a 64-dimensional point cloud, and these points are the projection of each data point along the directions with the largest variance.\n" \
                 "Essentially, we have found the optimal stretch and rotation in 64-dimensional space that allows us to see the layout of the digits in two dimensions, and have done this in an unsupervised manner—that is, without reference to the labels."
        python = 1

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _CellFactory


def CodeCellFactory(session):
    class _CellFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = Cell
            sqlalchemy_session = session

        index = 1
        cell_type = 'code'
        execution_count = 4
        lines = 1
        output_formats = "image/png;text/plain"
        source = "plt.contour(X, Y, Z, colors='black');"
        python = 1

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _CellFactory


def PythonFileFactory(session):
    class _PythonFileFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = PythonFile
            sqlalchemy_session = session

        name = 'python_file_1.py'
        source = 'import matplotlib\nprint("água")\n'
        total_lines = 2

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _PythonFileFactory


def RequirementFileFactory(session):
    class _RequirementFileFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = RequirementFile
            sqlalchemy_session = session

        name = 'requirements.txt'
        reqformat = 'requirements.txt'
        content = 'click\nSphinx\ncoverage\nawscli\nflake8\n'

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _RequirementFileFactory


def CellMarkdownFeatureFactory(session):
    class _CellMarkdownFeatureFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = CellMarkdownFeature
            sqlalchemy_session = session

        language = 'english'
        using_stopwords = 0
        len = 420
        lines = 2
        index = 0

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _CellMarkdownFeatureFactory


def CellModuleFactory(session):
    class _CellModuleFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = CellModule
            sqlalchemy_session = session

        line = 1
        import_type = 'import'
        module_name = 'matplotlib'
        local = 0

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _CellModuleFactory


def CellDataIOFactory(session):
    class _CellDataIOFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = CellDataIO
            sqlalchemy_session = session

        line = 1
        caller = 'pd'
        function_name = 'read_excel'
        function_type = 'Attribute'
        source = 'data.xlsx'

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _CellDataIOFactory


def PythonFileModuleFactory(session):
    class _PythonFileModuleFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = PythonFileModule
            sqlalchemy_session = session

        line = 1
        import_type = 'import'
        module_name = 'matplotlib'
        local = 0

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _PythonFileModuleFactory


def PythonFileDataIOFactory(session):
    class _PythonFileDataIOFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = PythonFileDataIO
            sqlalchemy_session = session

        line = 1
        caller = 'pd'
        function_name = 'read_excel'
        function_type = 'Attribute'
        source = 'data.xlsx'

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _PythonFileDataIOFactory
