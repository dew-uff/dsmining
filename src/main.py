"""Main script that calls the others"""
import subprocess
import sys
import os
from datetime import datetime

import src.config as config
from src.config import EXTRACTION_DIR
from src.db.database import connect, Repository
from src.helpers.h3_utils import check_exit, savepid, vprint
from src.classes.c2_status_logger import StatusLogger
from src.states import *

ORDER = [
    "s3_download",
    "e1_notebooks_and_cells",
    "e2_python_files",
    "e3_requirement_files",
    "e4_markdown_cells",
    "e5_code_cells",
    "e6_python_features",
]


def execute_script(script, args):
    """ Execute script and save log """
    moment = datetime.now().strftime("%Y%m%dT%H%M%S")
    print("[{}] Executing {}.py".format(moment, script))
    out = config.LOGS_DIR / ("{}-{}.outerr".format(script, moment))
    if out.exists():
        out = str(out) + ".2"

    with open(str(out), "wb") as outf:
        if script == 's3_download':
            options = ['python', '-u', config.SRC_DIR + os.sep + script + ".py"] + args
        else:
            options = ['python', '-u', EXTRACTION_DIR + os.sep + script + ".py"] + args

        status = subprocess.call(options, stdout=outf, stderr=outf)

        print("> Status", status)
        return status


def main():
    """Main function"""
    vprint(0, f"Starting main...")

    with connect() as session:
        query = session.query(Repository)
        vprint(1, f"Processed Repositories: {query.filter(Repository.state == REP_REQ_FILE_EXTRACTED).count()}")
        vprint(1, f"Failed Repositories: {query.filter(Repository.state in REP_ERRORS).count()}")
        vprint(1, f"Filtered Repositories: {query.filter(Repository.state == REP_FILTERED).count()} (yet to process)")

    with savepid():
        iteration = 0

        while query.filter(Repository.state == REP_FILTERED).count() > 0:
            filtered_repositories = query.filter(Repository.state == REP_FILTERED)
            iteration = iteration + 1
            iteration_repositories = []
            iteration_size = 0

            for rep in filtered_repositories:
                if iteration_size < 5 * (10 ** 6):
                    iteration_size = iteration_size + int(rep.disk_usage)
                    iteration_repositories.append(rep)

            vprint(2, f"Iteration {iteration}")
            vprint(2, f"Selected Repositories:"
                      f"{[repo.id for repo in iteration_repositories]}")
            print("a")

        result = []

        try:
            options_to_all = ['-i', '1', '10', '-e']

            to_execute = {
                script: []
                for script in ORDER
            }

            for script, args in to_execute.items():
                if check_exit({"all", "main", "main.py"}):
                    print("Found .exit file. Exiting")
                    return
                if script.endswith(".py"):
                    script = script[:-3]
                args = args + options_to_all
                status = execute_script(script, args)
                result.append("{} {} --> {}".format(script, " ".join(args), status))
            print("done")
        finally:
            status = StatusLogger("main closed")
            status.report()


if __name__ == "__main__":
    main()
