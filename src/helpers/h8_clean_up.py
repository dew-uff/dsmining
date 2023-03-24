import os
import shutil
from src.config import REPOS_DIR, DB_FILE, LOGS_DIR

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
        for file_name in os.listdir(LOGS_DIR):
            if file_name.endswith('.outerr'):
                file_path = os.path.join(LOGS_DIR, file_name)
                os.remove(file_path)
        print("Deleted logs")
