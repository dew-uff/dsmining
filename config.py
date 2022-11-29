import sys
import os
import dateutil.parser

if sys.version_info < (3, 5):
    from pathlib2 import Path
else:
    from pathlib import Path

# Github Credentials
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Directories
BASE = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = BASE + os.sep + 'src'
DB_DIR = BASE + os.sep + 'db'
LOGS_DIR = Path(BASE + os.sep + 'logs').expanduser()

DATA_DIR = BASE + os.sep + 'data'

REPOS_DIR = DATA_DIR + os.sep + 'repos'
JUPYTER_REPOS_DIR = Path(REPOS_DIR + os.sep + 'jupyter').expanduser()
PYTHON_REPOS_DIR = Path(REPOS_DIR + os.sep + 'python').expanduser()

RESOURCE_DIR = DATA_DIR + os.sep + 'resources'
REPOSITORIES_FILE = RESOURCE_DIR + os.sep + 'repositories.xlsx'
FILTERED_FILE = RESOURCE_DIR + os.sep + 'filtered_repositories.xlsx'
JUPYTER_REPOS_FILE = RESOURCE_DIR + os.sep + 'jupyter_repositories.xlsx'
PYTHON_REPOS_FILE = RESOURCE_DIR + os.sep + 'python_repositories.xlsx'

# Database
DB_CONNECTION = f'sqlite:////{DB_DIR}{os.sep}dbmining.sqlite'



# Directories
MACHINE = 'db'



# Config
VERBOSE = 5
FIRST_DATE = dateutil.parser.parse("2022-10-20")
MAX_SIZE = 10.0

# Additional Config
COMPRESSION = "lbzip2"
PYTHON_PATH = 'usr'
MOUNT_BASE = os.environ.get("JUP_MOUNT_BASE", "")
UMOUNT_BASE = os.environ.get("JUP_UMOUNT_BASE", "")


def read_interval(var, default=None):
    result = os.environ.get(var)
    if not result:
        return default
    return list(map(int, result.split(",")))


REPOSITORY_INTERVAL = read_interval("")

STATUS_FREQUENCY = {
    "extract_astroid": 5,
    "extract_ipython_and_modules": 5,
    "extract_notebooks_and_cells": 5,
    "extract_requirement_files": 5,
    "repository_crawler": 1,
    "clone_removed": 1,
    "compress": 5,
    "execute_repositories": 1,
}

VERSIONS = {
    2: {
        7: {
            15: "py27",
        },
    },
    3: {
        4: {
            5: "py34",
        },
        5: {
            5: "py35",
        },
        6: {
            5: "py36",
        },
        7: {
            0: "py37",
        },
    },
}
