import sys
import os

if sys.version_info < (3, 5):
    from pathlib2 import Path
else:
    from pathlib import Path

# GitHub Credentials
GITHUB = "github.com"
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
MACHINE = os.environ.get("GITHUB_USERNAME")

# Directories
CONFIG_DIR = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = os.path.dirname(CONFIG_DIR)
BASE = os.path.dirname(SRC_DIR)
ROOT = os.path.dirname(BASE)
EXTRACTION_DIR = SRC_DIR + os.sep + "extractions"

# Database
DB_DIR = SRC_DIR + os.sep + "db"
DB_FILE = DB_DIR + os.sep + "dbmining.sqlite"
DB_FILE_TEST = DB_DIR + os.sep + "dbmining_test.sqlite"
DB_CONNECTION = "sqlite:////{}".format(DB_FILE)
DB_CONNECTION_TEST = "sqlite:////{}".format(DB_FILE_TEST)


LOGS_DIR = Path(SRC_DIR + os.sep + "logs").expanduser()

QUERY_GRAPHQL_FILE = "{}/query.graphql".format(CONFIG_DIR)

REPOS_DIR = ROOT + os.sep + "repos"
SELECTED_REPOS_DIR = Path(REPOS_DIR + os.sep + "selected").expanduser()
TEST_REPOS_DIR = str(SELECTED_REPOS_DIR) + os.sep + "content" + os.sep + "test"


DATA_DIR = SRC_DIR + os.sep + "data"
RESOURCE_DIR = DATA_DIR + os.sep + "resources"
REPOSITORIES_FILE = RESOURCE_DIR + os.sep + "repositories.xlsx"
FILTERED_FILE = RESOURCE_DIR + os.sep + "filtered_repositories.xlsx"
SELECTED_REPOS_FILE = RESOURCE_DIR + os.sep + "selected_repositories.xlsx"


# Configs
VERBOSE = 5
COMPRESSION = "lbzip2"
ANACONDA_PATH = Path.home().joinpath("anaconda3")


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
            15: "dsm27",
        },
    },
    3: {
        5: {
            5: "dsm35",
        },
        8: {
            16: "dsm38",
        },
    },
}
