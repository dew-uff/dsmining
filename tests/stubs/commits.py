from datetime import datetime

from src.config.states import REP_LOADED


def stub_repo_commits():
    commits = [
        {'repository_id': None,
         'type': 'commit',
         'hash': '1a34a4f',
         'date': datetime(2018, 11, 30, 23, 26, 16),
         'author': 'Tester King',
         'message': 'Testing this'},

        {'repository_id': None,
         'type': 'commit',
         'hash': '2a34a4f',
         'date': datetime(2018, 11, 30, 23, 26, 16),
         'author': 'Tester King',
         'message': 'Testing this'},

        {'repository_id': None,
         'type': 'commit',
         'hash': '3a34a4f',
         'date': datetime(2018, 11, 30, 23, 26, 16),
         'author': 'Tester King',
         'message': 'Testing this'},
    ]

    return commits


def mock_load_rep_and_commits(_session, _repository, branch, commit, retry):
    _repository.state = REP_LOADED
    return None
