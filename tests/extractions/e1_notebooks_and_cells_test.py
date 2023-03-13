import sys
import os
import pytest
from src.db.database import Repository
from tests.database_test import connection, session
from tests.factories.models_test import RepositoryFactory

src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

class TestCellVisitorNewDataIO:

    def test(self, session):
        RepositoryFactory(session).create_batch(3)
        assert len(session.query(Repository).all()) == 3
        repositories = session.query(Repository).all()
        print(f"Total  repositories: {len(repositories)}")
