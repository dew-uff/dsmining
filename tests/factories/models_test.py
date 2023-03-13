import factory
from src.db.database import Repository

def RepositoryFactory(session):
    class _RepositoryFactory(factory.alchemy.SQLAlchemyModelFactory):
        class Meta:
            model = Repository
            sqlalchemy_session = session

        domain = "github.com"
        repository = factory.Sequence(lambda n: 'person{}/respository{}'.format(n+1, n+1))
        hash_dir1 = "8e"
        hash_dir2 = "3cb7dbc856becaff503a49f636d04d28043c2a"
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
