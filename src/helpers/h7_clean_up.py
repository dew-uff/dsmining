import os
import shutil
from src.config import REPOS_DIR, DB_FILE

REPOS = True
DATABASE = True

if REPOS:
   if os.path.exists(REPOS_DIR):
      shutil.rmtree(REPOS_DIR)
      print("Deleted Repositories")

if DATABASE:
   if os.path.exists(DB_FILE):
      os.remove(DB_FILE)
      print("Deleted database")
