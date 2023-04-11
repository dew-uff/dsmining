import os
import shutil
from src.config.consts import REPOS_DIR, DB_FILE, LOGS_DIR
from src.db.database import *

REPOS = True
DATABASE = True
LOGS = True

if REPOS:
    if os.path.exists(REPOS_DIR):
        shutil.rmtree(REPOS_DIR)
        print("Deleted Repositories")

if DATABASE:
    with connect() as session:
        for table in Base.metadata.sorted_tables:
            if table != Base.metadata.tables["queries"]:
                table.drop(session.connection())
        print("Dropped all tables but 'queries'")

if LOGS:
    if os.path.exists(LOGS_DIR):
        for root, dirs, files in os.walk(LOGS_DIR, topdown=False):
            for folder in dirs:
                shutil.rmtree(os.path.join(root, folder))
        print("Deleted logs")
