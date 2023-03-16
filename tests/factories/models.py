import factory
from src.db.database import Repository, Notebook, PythonFile, RequirementFile


def RepositoryFactory(session):
    class _RepositoryFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = Repository
            sqlalchemy_session = session

        domain = "github.com"
        repository = factory.Sequence(lambda n: 'person{}/respository{}'.format(n+1, n+1))
        hash_dir1 = "test"
        hash_dir2 = factory.Sequence(lambda n: "test_directory{}".format(n+1))
        commit = "8a34a4f653bdbdc01415a94dc20d4e9b97438965"
        is_mirror = 0
        disk_usage = 34707
        primary_language = "Jupyter Notebook"
        processed =  0

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _RepositoryFactory

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
        processed = 0


        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _NotebookFactory


def PythonFileFactory(session):
    class _PythonFileFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = PythonFile
            sqlalchemy_session = session

        name = 'python_file_1.py'
        source = 'import matplotlib\nprint("água")\n'
        total_lines = 2
        processed = 0

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
        processed = 0

        @factory.post_generation
        def commit_to_db(self, create, extracted, **kwargs):
            if create:
                session.add(self)
                session.commit()

    return _RequirementFileFactory
