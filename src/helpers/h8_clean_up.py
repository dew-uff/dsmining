import os
import sys
src_path = os.path.dirname(os.path.abspath(''))
if src_path not in sys.path:
    sys.path.append(src_path)

import shutil
from src.config.consts import REPOS_DIR, LOGS_DIR, DB_FILE, DB_RESTORED
from src.db.database import *

REPOS = True
DATABASE = True
LOGS = True

if REPOS:
    if os.path.exists(REPOS_DIR):
        shutil.rmtree(REPOS_DIR)
        print("Deleted Repositories")

if LOGS:
    if os.path.exists(LOGS_DIR):
        for root, dirs, files in os.walk(LOGS_DIR, topdown=False):
            for folder in dirs:
                shutil.rmtree(os.path.join(root, folder))
        print("Deleted logs")


if DATABASE:
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        shutil.copy2(DB_RESTORED, DB_FILE)
        print("Database restored to initial settings")


