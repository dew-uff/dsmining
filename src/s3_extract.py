""" Extracts Selected Repositories to Database """

import pandas as pd
from config import SELECTED_REPOS_FILE
from src import consts
from src.db.database import connect, Repository
from src.helpers.h1_utils import mount_basedir, SafeSession
from src.helpers.h2_load_repository import load_repository_and_commits
from src.states import REP_STOPPED

df = pd.read_excel(SELECTED_REPOS_FILE, keep_default_na=False)
print('Total repositories: ', len(df))

with connect() as session, mount_basedir():
    for repository in df.itertuples():
        load_repository_and_commits(
            SafeSession(session, interrupted=REP_STOPPED),
            "github.com", repository, commit='all')
        session.commit()


with connect() as session, mount_basedir():
    repositories = session.query(Repository).all()
    print(f"Total of downloaded repositories: {len(repositories)}")
