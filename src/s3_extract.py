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

from sqlalchemy import func, Integer, cast # noqa

from src.classes.c2_status_logger import StatusLogger
from src.config.consts import EXTRACTION_DIR, LOGS_DIR, MAIN_VERSION, MACHINE
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


def save_extraction(session, start, end, selected_repositories, error=False, failure=None):
    repositories_ids = [int(item) for item in selected_repositories if item.isdigit()]
    repositories = session.query(Repository).filter(Repository.id.in_(repositories_ids))

    if not error:
        extract = Extraction(
            start=start, end=end, runtime=end - start,
            repositores=len(repositories_ids),
            state=EXTRACTED_SUCCESS
        )

    else:
        extract = Extraction(
            start=start, end=end, runtime=end - start,
            repositores=len(repositories_ids),
            state=EXTRACTED_ERROR, failure=failure
        )

    session.add(extract)
    session.flush()

    repositories.update({Repository.extraction_id: extract.id}, synchronize_session=False)

    successfull_repos = repositories.filter(Repository.state == REP_REQ_FILE_EXTRACTED)
    successfull_repos.update({Repository.state: REP_FINISHED}, synchronize_session=False)

    session.commit()
    remove_repositorires(repositories)


def inform(session, iteration, selected_output):
    query = session.query(Repository)
    processed = query.filter(Repository.state == REP_FINISHED).count()
    inbetween = query.filter(Repository.state.in_(REP_EXTRACT_ORDER)).count()
    unprocessed = query.filter(Repository.state == REP_SELECTED).count()
    failed = query.filter(Repository.state.in_(REP_ERRORS)).count()

    # size_processed
    result_processed = query.filter(Repository.state == REP_FINISHED).with_entities(
        func.sum(func.cast(Repository.disk_usage, Integer))).one()[0]
    if result_processed is not None:
        size_processed = int(result_processed) / (10 ** 6)
    else:
        size_processed = 0

    # size_inbetween
    result_inbetween = query.filter(Repository.state.in_(REP_EXTRACT_ORDER)).with_entities(
        func.sum(func.cast(Repository.disk_usage, Integer))).one()[0]
    if result_inbetween is not None:
        size_inbetween = int(result_inbetween) / (10 ** 6)
    else:
        size_inbetween = 0

    # size_unprocessed
    result_unprocessed = query.filter(Repository.state == REP_SELECTED).with_entities(
        func.sum(func.cast(Repository.disk_usage, Integer))).one()[0]
    if result_unprocessed is not None:
        size_unprocessed = int(result_unprocessed) / (10 ** 6)
    else:
        size_unprocessed = 0

    # size_failed
    result_failed = query.filter(Repository.state.in_(REP_ERRORS)).with_entities(
        func.sum(func.cast(Repository.disk_usage, Integer))).one()[0]
    if result_failed is not None:
        size_failed = int(result_failed) / (10 ** 6)
    else:
        size_failed = 0

    total = size_processed + size_unprocessed + size_failed

    vprint(1, "Processed Repositories: {} ({:.2f}GB - {:.2f}%)"
           .format(processed, size_processed, (size_processed/total)*100),
           )
    vprint(1, "Inbetween Repositories: {} ({:.2f}GB - {:.2f}%)"
           .format(inbetween, size_inbetween, (size_inbetween / total) * 100)
           )
    vprint(1, "Unprocessed Repositories: {} ({:.2f}GB - {:.2f}%)"
           .format(unprocessed, size_unprocessed, (size_unprocessed/total)*100)
           )
    vprint(1, "Failed Repositories: {} ({:.2f}GB - {:.2f}%)\n\n"
           .format(failed, size_failed, (size_failed/total)*100)
           )

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

    out = path / "{}_{}_{}_{}.outerr".format(MACHINE, "itr"+str(iteration), script, start)
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
    filtered_repos = session.query(Repository).filter(Repository.state == REP_SELECTED)\
        .order_by(cast(Repository.disk_usage, Integer).desc())
    iteration_repositories = []
    iteration_size = 0
    options_to_all = ['-sr']

    # to set a limit of repositories per iteration
    limit = False
    count = 0

    for rep in filtered_repos:

        """
        disk_usage: The number of KBs (kilobytes) this repository occupies on disk.
        """
        if limit and count >= 100:
            break

        if iteration_size + int(rep.disk_usage) < SIZE_LIMIT:
            iteration_size = iteration_size + int(rep.disk_usage)
            iteration_repositories.append(rep)
            count = count + 1

    if len(iteration_repositories) == 0:
        return False, None

    ids = [repo.id for repo in iteration_repositories]

    selected_output = "Selected {} Repositories:{} ({:.2f}KB / {:.2f}MB / {:.2f}GB)"\
        .format(len(ids), ids, iteration_size, iteration_size / (10 ** 3), iteration_size / (10 ** 6))

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
                current_script = None
                for script, args in to_execute.items():
                    current_script = script

                    if check_exit({"all", "main", "main.py"}):
                        vprint(0, "Found .exit file. Exiting")
                        return

                    if script.endswith(".py"):
                        script = script[:-3]

                    args = args + selected_repositories
                    execute_script(script, args, iteration)
                end = datetime.utcnow()

                save_extraction(session, start, end, selected_repositories)
                vprint(4, "\033[92mRepositories from iteration {} extracted successfully!! Duration:{}\033[0m"
                       .format(iteration, end - start))

            except Exception as err:
                vprint(4, "\033[91mError extracting repositories from iteration {} \n{}\033[0m"
                       .format(iteration, err))

                end = datetime.utcnow()
                save_extraction(session, start, end, selected_repositories,
                                error=True, failure=current_script)

            vprint(4, "\033[93mFiles from {} were removed from memory.\033[0m"
                   .format(selected_output))
            selected_repositories, selected_output = select_repositories(session)

        stop = True
        vprint(4, "\033[92mDone!\033[0m")

        status = StatusLogger("main closed")
        status.report()


if __name__ == "__main__":
    main()
