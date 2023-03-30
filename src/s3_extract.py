"""Main script that calls the others"""
import shutil
import subprocess
import threading
import os
from datetime import datetime
import select
import sys

from sqlalchemy import func

from src.config.consts import EXTRACTION_DIR, SRC_DIR, LOGS_DIR
from src.db.database import connect, Repository, Extraction
from src.helpers.h3_utils import check_exit, savepid, vprint
from src.classes.c2_status_logger import StatusLogger
from src.config.states import *

stop = False

SIZE_LIMIT = 100 * (10 ** 3)  # 100 MB (since disk usage already comes in KB)

ORDER = [
    "e1_download",
    "e2_notebooks_and_cells",
    "e3_python_files",
    "e4_requirement_files",
    "e5_markdown_cells",
    "e6_code_cells",
    "e7_python_features",
]


def remove_repositorires(repositories):
    for rep in repositories:
        if rep.dir_path.exists():
            shutil.rmtree(os.path.join(rep.dir_path))


def save_extraction(session, start, end, selected_repositories, error=False):
    repositories_ids = [int(item) for item in selected_repositories if item.isdigit()]
    repositories = session.query(Repository).filter(Repository.id.in_(repositories_ids))

    if not error:
        extract = Extraction(
            start=start, end=end, runtime=end - start,
            repositores=len(selected_repositories),
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
    vprint(1, "Filtered Repositories: {} (yet to process)\n\n"
           .format(query.filter(Repository.state == REP_FILTERED).count()))
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

    out = path / "{}_{}_{}.outerr".format(str(iteration), script, start)
    if out.exists():
        out = str(out) + ".2"

    with open(str(out), "wb") as outf:
        if script == 's3_download':
            options = ['python', '-u', SRC_DIR + os.sep + script + ".py"] + args
        else:
            options = ['python', '-u', EXTRACTION_DIR + os.sep + script + ".py"] + args

        status = subprocess.call(options, stdout=outf, stderr=outf)
        end = datetime.now()

        vprint(0, "\033[93m[{}]\033[0m Done - Status: {} - Runtime: {}\n"
               .format(end.strftime('%Y-%m-%d %H:%M:%S'), status, str(end - start)))
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

    selected_output = "Selected Repositories:{} ({:.2f}KB / {:.2f}MB / {:.2f}GB)"\
        .format(ids, iteration_size, iteration_size / (10 ** 3), iteration_size / (10 ** 6))

    for id_ in ids:
        options_to_all.append(str(id_))

    return options_to_all, selected_output


def filtered_repositories(session):
    return session.query(Repository)\
        .filter(Repository.state == REP_FILTERED)\
        .count()


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
            vprint(2, "\033[92mThere are no filtered repositories to process.\033[0m")
            exit(0)

        input_thread = threading.Thread(target=get_stop)
        input_thread.start()
        vprint(0, "Starting main...\n")

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
