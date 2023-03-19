import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import DB_CONNECTION_TEST
from src.db.database import Base

engine = create_engine(DB_CONNECTION_TEST, convert_unicode=True, echo=False)
Session = sessionmaker(autocommit=False, autoflush=False)


@pytest.fixture(scope='function')
def connection():
    Base.metadata.create_all(engine)
    connection = engine.connect()
    yield connection
    connection.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope='function')
def session(connection):
    session = Session(bind=connection)
    yield session
    session.close()
