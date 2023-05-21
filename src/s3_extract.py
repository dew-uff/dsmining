"""
 - s3_extract.py

This script is responsible for extracting data from repositories
that were collected in `s1_collect.py` and then filtered and selected
in `s2_filter.py`.

It consists of loop that goes through the repositories in waves of a certing
SIZE_LIMIT that you can set. The extraction is done by executing a series of
extraction scripts that are located in the `src/extractions` folder in a certain
order that you can also set.

There's also a second thread that allows you two pause
the loop if and when you want to, by typing stop.
"""

import os
import sys
dir_path = os.path.dirname(os.path.abspath(''))
if dir_path not in sys.path:
    sys.path.append(dir_path)

import select
import subprocess
import threading
from datetime import datetime

from sqlalchemy import func

from src.classes.c2_status_logger import StatusLogger
from src.config.consts import EXTRACTION_DIR, LOGS_DIR, MAIN_VERSION
from src.config.states import *
from src.db.database import connect, Repository, Extraction
from src.helpers.h3_utils import check_exit, savepid, vprint, remove_repositorires

stop = False

SIZE_LIMIT = 500 * (10 ** 3)  # 100 MB (since disk usage already comes in KB)

ORDER = [
    "e1_download",
    "e2_notebooks_and_cells",
    "e3_python_files",
    "e4_requirement_files",
    "e5_markdown_cells",
    "e6_code_cells",
    "e7_python_features",
    "ag1_notebook_aggregate",
    "ag2_python_aggregate"
]


def save_extraction(session, start, end, selected_repositories, error=False):
    repositories_ids = [int(item) for item in selected_repositories if item.isdigit()]
    repositories = session.query(Repository).filter(Repository.id.in_(repositories_ids))

    if not error:
        extract = Extraction(
            start=start, end=end, runtime=end - start,
            repositores=len(repositories_ids),
            state=EXTRACTED_SUCCESS
        )

        session.add(extract)
        session.flush()

        repositories.update({Repository.extraction_id: extract.id}, synchronize_session=False)

        successfull_repos = repositories.filter(Repository.state == REP_REQ_FILE_EXTRACTED)
        successfull_repos.update({Repository.state: REP_FINISHED}, synchronize_session=False)

    else:
        extraction = Extraction(
            start=start, end=end, runtime=end - start,
            repositores=len(selected_repositories),
            state=EXTRACTED_ERROR
        )

        session.add(extraction)
    session.commit()
    remove_repositorires(repositories)


def inform(session, iteration, selected_output):
    query = session.query(Repository)
    vprint(1, "Processed Repositories: {}"
           .format(query.filter(Repository.state == REP_REQ_FILE_EXTRACTED).count()))
    vprint(1, "Failed Repositories: {}"
           .format(query.filter(Repository.state in REP_ERRORS).count()))
    vprint(1, "Unprocessed Repositories: {}\n\n"
           .format(query.filter(Repository.state == REP_SELECTED).count()))
    vprint(2, "Iteration {}".format(iteration))
    vprint(2, selected_output + "\n\n")


def execute_script(script, args, iteration):
    """ Execute script and save log """
    start = datetime.now()
    vprint(0, "\033[93m[{}]\033[0m Executing {}.py"
           .format(start.strftime('%Y-%m-%d %H:%M:%S'), script))
    path = LOGS_DIR / script
    if not os.path.exists(path):
        os.makedirs(path)

    out = path / "{}_{}_{}.outerr".format("itr"+str(iteration), script, start)
    if out.exists():
        out = str(out) + ".2"

    with open(str(out), "wb") as outf:
        python = MAIN_VERSION

        options = [str(python), '-u', EXTRACTION_DIR + os.sep + script + ".py"] + args

        status = subprocess.call(options, stdout=outf, stderr=outf)
        end = datetime.now()

        if status != 0:
            raise Exception("Extraction failed.")

        vprint(0, "\033[93m[{}]\033[0m Done - Status: {} - Runtime: {}\n"
               .format(end.strftime('%Y-%m-%d %H:%M:%S'), status, str(end - start)))
        return status


def filtered_repositories(session):
    return session.query(Repository)\
        .filter(Repository.state == REP_SELECTED)\
        .count()


def select_repositories(session):
    filtered_repos = session.query(Repository).filter(Repository.state == REP_SELECTED)
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

    selected_output = "Selected Repositories:{} ({:.2f}KB / {:.2f}MB / {:.2f}GB)"\
        .format(ids, iteration_size, iteration_size / (10 ** 3), iteration_size / (10 ** 6))

    for id_ in ids:
        options_to_all.append(str(id_))

    return options_to_all, selected_output


def get_stop():
    global stop
    vprint(4, "\033[93mIf you want to stop the execution type 'stop'\033[0m")
    while not stop:
        if select.select([sys.stdin, ], [], [], 0.0)[0]:
            user_input = input()
            if user_input == "stop":
                vprint(4, "\033[91mStopping execution on the next iteration.\033[0m")
                vprint(4, "\033[93mFinishing the current iteration.\033[0m")
                stop = True


def main():
    """ Main function """
    with connect() as session, savepid():

        global stop
        to_execute = {script: [] for script in ORDER}
        selected_repositories, selected_output = select_repositories(session)

        if not selected_repositories:
            vprint(2, "\033[92mThere are no selected repositories to process.\033[0m")
            exit(0)

        input_thread = threading.Thread(target=get_stop)
        input_thread.start()
        vprint(0, "Starting extraction...\n")

        while filtered_repositories(session) > 0 and selected_repositories and not stop:
            try:
                previous_iteration = session.query(func.max(Extraction.id)).scalar()
                iteration = (previous_iteration + 1) if previous_iteration is not None else 1
                inform(session, iteration, selected_output)

                start = datetime.utcnow()
                for script, args in to_execute.items():
                    if check_exit({"all", "main", "main.py"}):
                        vprint(0, "Found .exit file. Exiting")
                        return

                    if script.endswith(".py"):
                        script = script[:-3]

                    args = args + selected_repositories
                    execute_script(script, args, iteration)
                end = datetime.utcnow()

                save_extraction(session, start, end, selected_repositories)
                vprint(4, "\033[92mRepositories from iteration {} extracted successfully!!\033[0m"
                       .format(iteration))

            except Exception as err:
                vprint(4, "\033[91mError extracting repositories from iteration {} \n{}\033[0m"
                       .format(iteration, err))

                end = datetime.utcnow()
                save_extraction(session, start, end, selected_repositories, error=True)

            vprint(4, "\033[93mFiles from {} were removed from memory.\033[0m"
                   .format(selected_output))
            selected_repositories, selected_output = select_repositories(session)

        stop = True
        vprint(4, "\033[92mDone!\033[0m")

        status = StatusLogger("main closed")
        status.report()


if __name__ == "__main__":
    main()
