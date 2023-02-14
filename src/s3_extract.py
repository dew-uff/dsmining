import pandas as pd

from config import SELECTED_REPOS_FILE
from src.db.database import connect, Repository
from h1_utils import mount_basedir
from h2_load_repository import load_repository

df = pd.read_excel(SELECTED_REPOS_FILE, keep_default_na=False)
print('Total repositories: ',len(df))

with connect() as session, mount_basedir():
    for repository in df.itertuples():
        full_name = f'{repository.owner}/{repository.name}'
        load_repository(session, "github.com", full_name)
        session.commit()


with connect() as session, mount_basedir():
    repositories = session.query(Repository).all()
    print(f"Total of downloaded repositories: {len(repositories)}")