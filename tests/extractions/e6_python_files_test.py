import sys
import os

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path: sys.path.append(src)

import src.consts as consts
import src.extractions.e6_python_features as e6

from src.helpers.h1_utils import TimeoutError
from src.classes.c2_local_checkers import PathLocalChecker
from src.extractions.e6_python_features import process_python_file
from src.db.database import PythonFileModule, PythonFileDataIO
from tests.factories.models import RepositoryFactory, PythonFileFactory
from tests.factories.models import PythonFileModuleFactory, PythonFileDataIOFactory
from tests.database_config import connection, session



class TestE6PythonFilesExtract:
    def test_process_python_file(self, session):
        module_name = 'pandas'
        caller, function_name, source  = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id,
            source=f"import {module_name} as pd\ndf={caller}.{function_name}({source})"
        )

        checker = PathLocalChecker("")
        result = process_python_file(session=session, repository_id=repository.id,
                                     python_file=python_file, checker=checker)
        session.commit()
        module = session.query(PythonFileModule).first()
        data_io = session.query(PythonFileDataIO).first()

        assert result == 'done'
        assert python_file.processed == consts.PF_PROCESS_OK

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
            processed=consts.PF_PROCESS_OK
        )
        checker = PathLocalChecker("")
        result = process_python_file(session=session, repository_id=repository.id,
                                     python_file=python_file, checker=checker)
        session.commit()

        assert result == 'already processed'
        assert python_file.processed == consts.PF_PROCESS_OK


    def test_process_python_file_time_out(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id
        )
        checker = PathLocalChecker("")

        def mock_extract(_source, _checker):
            raise TimeoutError
        monkeypatch.setattr(e6, 'extract_features', mock_extract)

        result = process_python_file(session=session, repository_id=repository.id,
                                     python_file=python_file, checker=checker)
        session.commit()

        assert result == 'Failed due to  Time Out Error.'
        assert python_file.processed == consts.PF_TIMEOUT


    def test_process_python_file_syntax_error(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id
        )
        checker = PathLocalChecker("")

        def mock_extract(_source, _checker):
            raise SyntaxError
        monkeypatch.setattr(e6, 'extract_features', mock_extract)

        result = process_python_file(session=session, repository_id=repository.id,
                                     python_file=python_file, checker=checker)
        session.commit()

        assert result == 'Failed due to Syntax Error.'
        assert python_file.processed == consts.PF_SYNTAX_ERROR


    def test_process_python_file_other_errors(self, session, monkeypatch):
        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id
        )
        checker = PathLocalChecker("")

        def mock_extract(_source, _checker):
            raise ValueError
        monkeypatch.setattr(e6, 'extract_features', mock_extract)

        result = process_python_file(session=session, repository_id=repository.id,
                                     python_file=python_file, checker=checker)
        session.commit()

        assert 'Failed to process' in result
        assert python_file.processed == consts.PF_PROCESS_ERROR

    def test_process_python_file_retry_process_error(self,session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id, processed=consts.PF_PROCESS_ERROR,
            source=f"import {module_name} as pd\ndf={caller}.{function_name}({source})"
        )
        checker = PathLocalChecker("")

        python_file_module = PythonFileModuleFactory(session).create(repository_id=repository.id,
                                                                     python_file_id=python_file.id)
        python_file_data_io = PythonFileDataIOFactory(session).create(repository_id=repository.id,
                                                                      python_file_id=python_file.id)
        pm_created_at = python_file_module.created_at
        pd_created_at = python_file_data_io.created_at

        result = process_python_file(session=session, repository_id=repository.id,
                                   python_file=python_file, checker=checker,
                                   skip_if_error=0)
        session.commit()
        module = session.query(PythonFileModule).first()
        data_io = session.query(PythonFileDataIO).first()

        assert result == 'done'
        assert python_file.processed == consts.C_PROCESS_OK

        assert module.python_file_id == python_file.id
        assert pm_created_at != module.created_at

        assert data_io.python_file_id == python_file.id
        assert pd_created_at != data_io.created_at

    def test_process_python_file_retry_process_syntax(self,session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id, processed=consts.PF_SYNTAX_ERROR,
            source=f"import {module_name} as pd\ndf={caller}.{function_name}({source})"
        )
        checker = PathLocalChecker("")

        python_file_module = PythonFileModuleFactory(session).create(repository_id=repository.id,
                                                                     python_file_id=python_file.id)
        python_file_data_io = PythonFileDataIOFactory(session).create(repository_id=repository.id,
                                                                      python_file_id=python_file.id)
        pm_created_at = python_file_module.created_at
        pd_created_at = python_file_data_io.created_at

        result = process_python_file(session=session, repository_id=repository.id,
                                   python_file=python_file, checker=checker,
                                   skip_if_syntaxerror=0)
        session.commit()
        module = session.query(PythonFileModule).first()
        data_io = session.query(PythonFileDataIO).first()

        assert result == 'done'
        assert python_file.processed == consts.C_PROCESS_OK

        assert module.python_file_id == python_file.id
        assert pm_created_at != module.created_at

        assert data_io.python_file_id == python_file.id
        assert pd_created_at != data_io.created_at

    def test_process_python_file_retry_process_timeout(self,session):
        module_name = 'pandas'
        caller, function_name, source = 'pd', 'read_csv', "'data.csv'"

        repository = RepositoryFactory(session).create()
        python_file = PythonFileFactory(session).create(
            repository_id=repository.id, processed=consts.PF_TIMEOUT,
            source=f"import {module_name} as pd\ndf={caller}.{function_name}({source})"
        )
        checker = PathLocalChecker("")

        python_file_module = PythonFileModuleFactory(session).create(repository_id=repository.id,
                                                                     python_file_id=python_file.id)
        python_file_data_io = PythonFileDataIOFactory(session).create(repository_id=repository.id,
                                                                      python_file_id=python_file.id)
        pm_created_at = python_file_module.created_at
        pd_created_at = python_file_data_io.created_at

        result = process_python_file(session=session, repository_id=repository.id,
                                     python_file=python_file, checker=checker, skip_if_timeout=0)
        session.commit()
        module = session.query(PythonFileModule).first()
        data_io = session.query(PythonFileDataIO).first()

        assert result == 'done'
        assert python_file.processed == consts.C_PROCESS_OK

        assert module.python_file_id == python_file.id
        assert pm_created_at != module.created_at

        assert data_io.python_file_id == python_file.id
        assert pd_created_at != data_io.created_at