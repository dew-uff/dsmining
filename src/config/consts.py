import sys
import os

if sys.version_info < (3, 5):
    from pathlib2 import Path
else:
    from pathlib import Path  # noqa

# GitHub Credentials
GITHUB = "github.com"
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
MACHINE = "luam"

# Directories
CONFIG_DIR = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = os.path.dirname(CONFIG_DIR)
BASE = os.path.dirname(SRC_DIR)
ROOT = os.path.dirname(BASE)
EXTRACTION_DIR = SRC_DIR + os.sep + "extractions"
OUTPUTS_DIR = SRC_DIR + os.sep + "outputs"

# Database
DB_DIR = SRC_DIR + os.sep + "db"
DB_FILE = DB_DIR + os.sep + "dsmining.sqlite"
DB_RESTORED = ROOT + os.sep + "dsmining.sqlite"
DB_FILE_TEST = DB_DIR + os.sep + "dsmining_test.sqlite"
DB_CONNECTION = "sqlite:////{}".format(DB_FILE)
DB_CONNECTION_TEST = "sqlite:////{}".format(DB_FILE_TEST)

# Configs
REPOS_DIR = ROOT + os.sep + "repos"
SELECTED_REPOS_DIR = Path(REPOS_DIR + os.sep + "selected").expanduser()
TEST_REPOS_DIR = str(SELECTED_REPOS_DIR) + os.sep + "content" + os.sep + "test"
LOGS_DIR = Path(SRC_DIR + os.sep + "logs").expanduser()
QUERY_GRAPHQL_FILE = "{}/query.graphql".format(CONFIG_DIR)
VERBOSE = 5
STATUS_FREQUENCY = 5
COMPRESSION = "lbzip2"
ANACONDA_PATH = Path.home().joinpath("anaconda3")
MAIN_VERSION = ANACONDA_PATH / "envs" / "dsm38" / "bin" / "python"

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
