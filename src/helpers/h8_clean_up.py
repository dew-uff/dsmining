import os
import shutil
from src.config.consts import REPOS_DIR, DB_FILE, LOGS_DIR

REPOS = True
DATABASE = True
LOGS = True

if REPOS:
    if os.path.exists(REPOS_DIR):
        shutil.rmtree(REPOS_DIR)
        print("Deleted Repositories")

if DATABASE:
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("Deleted database")

if LOGS:
    if os.path.exists(LOGS_DIR):
        for root, dirs, files in os.walk(LOGS_DIR, topdown=False):
            for folder in dirs:
                shutil.rmtree(os.path.join(root, folder))
        print("Deleted logs")
