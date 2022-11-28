import sys
import os
import dateutil.parser

if sys.version_info < (3, 5):
    from pathlib2 import Path
else:
    from pathlib import Path

# Database
DB_CONNECTION = 'sqlite:///dbmining.sqlite'

# Github Credentials
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


# Directories
MACHINE = 'db'
SRC_DIR = os.path.dirname(os.path.realpath(__file__))
BASE = os.path.dirname(SRC_DIR)
BASE_DIR = Path("./mnt/jupyter/github").expanduser()
LOGS_DIR = Path("./jupyter/logs").expanduser()
WORKSPACE_DIR = os.path.dirname(BASE)
REPOS_DIR = WORKSPACE_DIR + os.sep + 'repos'
RESOURCE_DIR = BASE + os.sep + 'resources'
PROJECTS_FILE = RESOURCE_DIR + os.sep + 'projects.xlsx'
FILTERED_FILE = RESOURCE_DIR + os.sep + 'filtered_projects.xlsx'
ANNOTATED_FILE = RESOURCE_DIR + os.sep + 'annotated.xlsx'
JUPYTER_FILE = RESOURCE_DIR + os.sep + 'jupyter.xlsx'

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
