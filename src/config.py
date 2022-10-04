#!/usr/bin/env upython
import argparse
import subprocess
import sys
import os
import dateutil.parser

if sys.version_info < (3, 5):
    from pathlib2 import Path
else:
    from pathlib import Path

IS_SQLITE = True
DB_CONNECTION = 'sqlite:///projects/db.sqlite'

# Directories
SRC_DIR = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = os.path.dirname(SRC_DIR)
WORKSPACE_DIR = os.path.dirname(BASE_DIR)
REPOS_DIR = WORKSPACE_DIR + os.sep + 'repos'
RESOURCE_DIR = BASE_DIR + os.sep + 'resources'
# Files
PROJECTS_FILE = RESOURCE_DIR + os.sep + 'projects.xlsx'
FILTERED_FILE = RESOURCE_DIR + os.sep + 'filtered_projects.xlsx'
ANNOTATED_FILE = RESOURCE_DIR + os.sep + 'annotated.xlsx'
DATABASE_CONFIG_FILE = BASE_DIR + os.sep + 'database.json'
JUPYTER_FILE = RESOURCE_DIR + os.sep + 'jupyter.xlsx'
