import os
import shutil

REPOS = True
DATABASE = True

if REPOS:
   if os.path.exists("data/repos/selected"):
      shutil.rmtree("data/repos/selected")

if DATABASE:
   if os.path.exists("db/dbmining.sqlite"):
      os.remove("db/dbmining.sqlite")
