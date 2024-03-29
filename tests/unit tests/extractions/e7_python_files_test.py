import os
import sys

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import src.extractions.e7_python_features as e7

from src.config.states import *
from src.helpers.h3_utils import TimeoutError
from src.classes.c4_local_checkers import PathLocalChecker
from src.extractions.e7_python_features import process_python_file
from src.db.database import PythonFileModule, PythonFileDataIO
from tests.database_config import connection, session  # noqa: F401
from tests.factories.models import RepositoryFactory, PythonFileFactory
from tests.factories.models import PythonFileModuleFactory, PythonFileDataIOFactory


class TestPythonFilesExtract:
    def test_process_python_file(self, session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', 'data.csv'

        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id,
            source="import {} as pd\ndf={}.{}('{}')".format(module_name, caller, function_name, source),
            state=PF_LOADED
        )

        checker = PathLocalChecker("")
        dispatches = set()

        result = process_python_file(session=session, dispatches=dispatches,
                                     repository_id=repository.id, python_file=python_file,
                                     checker=checker)
        session.commit()
        module = session.query(PythonFileModule).first()
        data_io = session.query(PythonFileDataIO).first()

        assert result == 'done'
        assert python_file.state == PF_PROCESSED
        assert python_file.extracted_args == 1
        assert python_file.missed_args == 0

        assert module.python_file_id == python_file.id
        assert module.module_name == module_name
        assert module.import_type == "import"

        assert data_io.python_file_id == python_file.id
        assert data_io.caller == caller
        assert data_io.function_name == function_name
        assert data_io.source == source

    def test_process_python_file_already_processed(self, session):
        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id,
            state=PF_PROCESSED
        )
        checker = PathLocalChecker("")
        dispatches = set()

        result = process_python_file(session=session, dispatches=dispatches,
                                     repository_id=repository.id, python_file=python_file,
                                     checker=checker)
        session.commit()

        assert result == 'already processed'
        assert python_file.state == PF_PROCESSED

    def test_process_python_file_time_out(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id,
            state=PF_LOADED
        )
        checker = PathLocalChecker("")
        dispatches = set()

        def mock_extract(_source, _checker):
            raise TimeoutError

        monkeypatch.setattr(e7, 'extract_features', mock_extract)

        result = process_python_file(session=session, dispatches=dispatches,
                                     repository_id=repository.id, python_file=python_file,
                                     checker=checker)
        session.commit()

        assert result == 'Failed due to  Time Out Error.'
        assert python_file.state == PF_PROCESS_TIMEOUT

    def test_process_python_file_syntax_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id,
            state=PF_LOADED
        )
        checker = PathLocalChecker("")
        dispatches = set()

        def mock_extract(_source, _checker):
            raise SyntaxError

        monkeypatch.setattr(e7, 'extract_features', mock_extract)

        result = process_python_file(session=session, dispatches=dispatches,
                                     repository_id=repository.id, python_file=python_file,
                                     checker=checker)
        session.commit()
        dispatches = list(dispatches)

        assert 'Dispatched to' in result
        assert len(dispatches) == 1
        assert dispatches[0][0] == python_file.id
        assert "dsm27" in dispatches[0][1]
        assert python_file.state == PF_LOADED

    def test_process_python_file_other_errors(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id,
            state=PF_LOADED
        )
        checker = PathLocalChecker("")
        dispatches = set()

        def mock_extract(_source, _checker):
            raise ValueError

        monkeypatch.setattr(e7, 'extract_features', mock_extract)

        result = process_python_file(session=session, dispatches=dispatches,
                                     repository_id=repository.id, python_file=python_file,
                                     checker=checker)
        session.commit()

        assert 'Failed to process' in result
        assert python_file.state == PF_PROCESS_ERROR

    def test_process_python_file_retry_process_error(self, session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', 'data.csv'

        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id, state=PF_PROCESS_ERROR,
            source="import {} as pd\ndf={}.{}('{}')".format(module_name, caller, function_name, source),
        )
        checker = PathLocalChecker("")
        dispatches = set()

        python_file_module = PythonFileModuleFactory(session).create(repository_id=repository.id,
                                                                     python_file_id=python_file.id)
        python_file_data_io = PythonFileDataIOFactory(session).create(repository_id=repository.id,
                                                                      python_file_id=python_file.id)
        pm_created_at = python_file_module.created_at
        pd_created_at = python_file_data_io.created_at

        result = process_python_file(session=session, dispatches=dispatches,
                                     repository_id=repository.id, python_file=python_file,
                                     checker=checker, retry_error=True)
        session.commit()
        module = session.query(PythonFileModule).first()
        data_io = session.query(PythonFileDataIO).first()

        assert result == 'done'
        assert python_file.state == PF_PROCESSED
        assert python_file.extracted_args == 1
        assert python_file.missed_args == 0

        assert module.python_file_id == python_file.id
        assert pm_created_at != module.created_at

        assert data_io.python_file_id == python_file.id
        assert pd_created_at != data_io.created_at

    def test_process_python_file_retry_process_syntax(self, session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', 'data.csv'

        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id, state=PF_SYNTAX_ERROR,
            source="import {} as pd\ndf={}.{}('{}')".format(module_name, caller, function_name, source),
        )
        checker = PathLocalChecker("")
        dispatches = set()

        python_file_module = PythonFileModuleFactory(session).create(repository_id=repository.id,
                                                                     python_file_id=python_file.id)
        python_file_data_io = PythonFileDataIOFactory(session).create(repository_id=repository.id,
                                                                      python_file_id=python_file.id)
        pm_created_at = python_file_module.created_at
        pd_created_at = python_file_data_io.created_at

        result = process_python_file(session=session, dispatches=dispatches,
                                     repository_id=repository.id, python_file=python_file,
                                     checker=checker, retry_syntax_error=True)
        session.commit()
        module = session.query(PythonFileModule).first()
        data_io = session.query(PythonFileDataIO).first()

        assert result == 'done'
        assert python_file.state == PF_PROCESSED
        assert python_file.extracted_args == 1
        assert python_file.missed_args == 0

        assert module.python_file_id == python_file.id
        assert pm_created_at != module.created_at

        assert data_io.python_file_id == python_file.id
        assert pd_created_at != data_io.created_at

    def test_process_python_file_retry_process_timeout(self, session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id, state=PF_PROCESS_TIMEOUT,
            source="import {} as pd\ndf={}.{}({})".format(module_name, caller, function_name, source),
        )
        checker = PathLocalChecker("")
        dispatches = set()

        python_file_module = PythonFileModuleFactory(session).create(repository_id=repository.id,
                                                                     python_file_id=python_file.id)
        python_file_data_io = PythonFileDataIOFactory(session).create(repository_id=repository.id,
                                                                      python_file_id=python_file.id)
        pm_created_at = python_file_module.created_at
        pd_created_at = python_file_data_io.created_at

        result = process_python_file(session=session, dispatches=dispatches,
                                     repository_id=repository.id, python_file=python_file,
                                     checker=checker, retry_timeout=True)
        session.commit()
        module = session.query(PythonFileModule).first()
        data_io = session.query(PythonFileDataIO).first()

        assert result == 'done'
        assert python_file.state == PF_PROCESSED
        assert python_file.extracted_args == 1
        assert python_file.missed_args == 0

        assert module.python_file_id == python_file.id
        assert pm_created_at != module.created_at

        assert data_io.python_file_id == python_file.id
        assert pd_created_at != data_io.created_at

