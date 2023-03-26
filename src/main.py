"""Main script that calls the others"""
import subprocess
import threading
import os
from datetime import datetime
import select
import sys

import src.config as config
from src.config import EXTRACTION_DIR, SRC_DIR
from src.db.database import connect, Repository
from src.helpers.h3_utils import check_exit, savepid, vprint
from src.classes.c2_status_logger import StatusLogger
from src.states import *

stop = False

SIZE_LIMIT = 100 * (10 ** 3)  # 100 MB (since disk usage already comes in KB)

ORDER = [
    "s3_download",
    "e1_notebooks_and_cells",
    "e2_python_files",
    "e3_requirement_files",
    "e4_markdown_cells",
    "e5_code_cells",
    "e6_python_features",
]


def inform(session, iteration, selected_output):
    query = session.query(Repository)
    vprint(1, f"Processed Repositories: {query.filter(Repository.state == REP_REQ_FILE_EXTRACTED).count()}")
    vprint(1, f"Failed Repositories: {query.filter(Repository.state in REP_ERRORS).count()}")
    vprint(1, f"Filtered Repositories: {query.filter(Repository.state == REP_FILTERED).count()}"
              f" (yet to process)\n\n")
    vprint(2, f"Iteration {iteration}")
    vprint(2, selected_output + "\n\n")


def execute_script(script, args, iteration):
    """ Execute script and save log """
    start = datetime.now()
    print(f"\033[93m[{start.strftime('%Y-%m-%d %H:%M:%S')}]\033[0m Executing {script}.py")
    path = config.LOGS_DIR / script
    if not os.path.exists(path):
        os.makedirs(path)

    out = path / f"{str(iteration)}_{script}_{start}.outerr"
    if out.exists():
        out = str(out) + ".2"

    with open(str(out), "wb") as outf:
        if script == 's3_download':
            options = ['python', '-u', SRC_DIR + os.sep + script + ".py"] + args
        else:
            options = ['python', '-u', EXTRACTION_DIR + os.sep + script + ".py"] + args

        status = subprocess.call(options, stdout=outf, stderr=outf)
        end = datetime.now()
        print(f"\033[93m[{end.strftime('%Y-%m-%d %H:%M:%S')}]\033[0m Done - Status: {status} "
              f"- Runtime: { str(end-start)}\n")
        return status


def select_repositories(session):
    filtered_repos = session.query(Repository).filter(Repository.state == REP_FILTERED)
    iteration_repositories = []
    iteration_size = 0
    options_to_all = ['-sr']

    for rep in filtered_repos:

        """
        disk_usage: The number of KBs (kilobytes) this repository occupies on disk.
        """

        if iteration_size + int(rep.disk_usage) < SIZE_LIMIT:
            iteration_size = iteration_size + int(rep.disk_usage)
            iteration_repositories.append(rep)

    if len(iteration_repositories) == 0:
        return False, None

    ids = [repo.id for repo in iteration_repositories]

    selected_output = f"Selected Repositories:"\
                      f"{ids} ({iteration_size}KB /"\
                      f" {(iteration_size / (10 ** 3)):.2f}MB /"\
                      f" {(iteration_size / (10 ** 6)):.2f}GB)"

    for id_ in ids:
        options_to_all.append(str(id_))

    return options_to_all, selected_output


def filtered_repositories(session):
    return session.query(Repository)\
        .filter(Repository.state == REP_FILTERED)\
        .count()


def get_stop():
    global stop
    vprint(4, "\033[93mIf you want to stop execution type 'stop'\033[0m")
    while not stop:
        if select.select([sys.stdin, ], [], [], 0.0)[0]:
            user_input = input()
            if user_input == "stop":
                vprint(4, "\033[91mStopping execution on the next iteration.\033[0m")
                vprint(4, "\033[93mFinishing the currrent iteration.\033[0m")
                stop = True


def main():
    """Main function"""
    with connect() as session:
        with savepid():
            global stop
            iteration = 0
            to_execute = {script: [] for script in ORDER}
            selected_repositories, selected_output = select_repositories(session)

            if not selected_repositories:
                vprint(2, "\033[92mThere are no filtered repositories to process.\033[0m")
                exit(0)

            input_thread = threading.Thread(target=get_stop)
            input_thread.start()
            vprint(0, f"Starting main...\n")

            while filtered_repositories(session) > 0 and selected_repositories and not stop:
                try:
                    iteration = iteration + 1
                    inform(session, iteration, selected_output)
                    for script, args in to_execute.items():
                        if check_exit({"all", "main", "main.py"}):
                            print("Found .exit file. Exiting")
                            return

                        if script.endswith(".py"):
                            script = script[:-3]

                        args = args + selected_repositories
                        execute_script(script, args, iteration)

                except Exception as err:
                    print(err)

                selected_repositories, selected_output = select_repositories(session)

            input_thread = None
            stop = True
            vprint(4, "\033[92mDone!\033[0m")

            status = StatusLogger("main closed")
            status.report()


if __name__ == "__main__":
    main()
