import sys
import os
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import src.consts as consts
from src.db.database import Repository
from src.helpers.h1_utils import SafeSession
from tests.database_test import connection, session
from tests.factories.models_test import RepositoryFactory
from src.helpers.h2_script_helpers import filter_repositories


class TestH2ScripHelpersFilterRepositories:

    def test_filter_all(self, session):
        rep1, rep2 = RepositoryFactory(session).create_batch(2)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session = SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories = True,
            skip_if_error=consts.R_N_ERROR,
            count = False,
            interval = None,
            reverse=False,
            skip_already_processed = consts.R_N_EXTRACTION
        )

        assert query.count() == 2
        assert rep1 in query.all()
        assert rep2 in query.all()

    def test_filter_count(self, session, capsys):
        RepositoryFactory(session).create_batch(3)

        assert len(session.query(Repository).all()) == 3

        filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=True,
            interval=None,
            reverse=False,
            skip_already_processed = consts.R_N_EXTRACTION
        )

        captured = capsys.readouterr()
        assert captured.out == "3\n"

    def test_filter_reverse(self, session):
        rep1, rep2 = RepositoryFactory(session).create_batch(2)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=None,
            reverse=True,
            skip_already_processed = consts.R_N_EXTRACTION
        )

        assert query.count() == 2
        assert rep1 is query[1]
        assert rep2 is query[0]

    def test_filter_inteval(self, session):
        reps = RepositoryFactory(session).create_batch(10)

        assert len(session.query(Repository).all()) == 10

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=[3,6],
            reverse=False,
            skip_already_processed=consts.R_N_EXTRACTION
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
            session = SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                     11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                                     21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                                     31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
            skip_if_error=consts.R_N_ERROR,
            count = False,
            interval = None,
            reverse=False,
            skip_already_processed = consts.R_N_EXTRACTION
        )

        assert selected_repositories == [31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
        assert query.count() == 30

        new_selected_repositories, new_query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=selected_repositories,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=None,
            reverse=False,
            skip_already_processed=consts.R_N_EXTRACTION
        )

        assert new_selected_repositories ==[]
        assert new_query.count() == 10

    def test_filter_filters_skip_if_error(self,session):
        rep = RepositoryFactory(session).create()
        rep_erro = RepositoryFactory(session).create(processed=consts.R_N_ERROR)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=None,
            reverse=False,
            skip_already_processed=consts.R_N_EXTRACTION
        )

        assert query.count() == 1
        assert rep_erro not in query
        assert rep in query

    def test_filter_filters_skip_already_processed(self,session):
        rep = RepositoryFactory(session).create()
        rep_processed = RepositoryFactory(session).create(processed=consts.R_N_EXTRACTION)

        assert len(session.query(Repository).all()) == 2

        selected_repositories, query = filter_repositories(
            session=SafeSession(session, interrupted=consts.N_STOPPED),
            selected_repositories=True,
            skip_if_error=consts.R_N_ERROR,
            count=False,
            interval=None,
            reverse=False,
            skip_already_processed=consts.R_N_EXTRACTION
        )

        assert query.count() == 1
        assert rep_processed not in query
        assert rep in query
