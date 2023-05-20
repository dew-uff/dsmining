import os
import sys
src_path = os.path.dirname(os.path.abspath(''))
if src_path not in sys.path:
    sys.path.append(src_path)

import shutil
from src.config.consts import REPOS_DIR, LOGS_DIR
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
            if table != Base.metadata.tables["repositories"]:
                table.drop(session.connection())
        print("Dropped all tables but 'repositories'")

if LOGS:
    if os.path.exists(LOGS_DIR):
        for root, dirs, files in os.walk(LOGS_DIR, topdown=False):
            for folder in dirs:
                shutil.rmtree(os.path.join(root, folder))
        print("Deleted logs")
