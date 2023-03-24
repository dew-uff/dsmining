""" Extracts Requirement Files from repositories """
import os
import argparse
import chardet
import src.config as config

from src.states import *
from src.db.database import RequirementFile, connect
from src.helpers.h3_utils import vprint, savepid
from src.classes.c2_status_logger import StatusLogger
from src.helpers.h3_utils import find_files_in_path, unzip_repository
from src.helpers.h2_script_helpers import apply, set_up_argument_parser


def find_requirements(session, repository):
    setups, requirements, pipfiles, pipfile_locks = [], [], [], []

    if not repository.path.exists():
        msg = unzip_repository(session, repository)
        if msg != "done":
            vprint(2, "repository not found")
            repository.state = REP_UNAVAILABLE_FILES
            session.add(repository)
            session.commit()
            return setups, requirements, pipfiles, pipfile_locks

    setups, requirements, pipfiles, pipfile_locks = find_files_in_path(
        repository.path, ["setup.py", "requirements.txt", "Pipfile", "Pipfile.lock"])

    repository.setups_count = len(setups)
    repository.requirements_count = len(requirements)
    repository.pipfiles_count = len(pipfiles)
    repository.pipfile_locks_count = len(pipfile_locks)

    session.add(repository)
    session.commit()
    return setups, requirements, pipfiles, pipfile_locks


def process_requirement_files(session, repository, req_names, reqformat):
    """ Processes a requirement file """
    for item in req_names:
        name = str(item)

        if not name:
            continue

        requirement_file = session.query(RequirementFile).filter(
            RequirementFile.repository_id == repository.id,
            RequirementFile.name == name,
        ).first()

        if requirement_file is not None:
            if requirement_file.state == REQ_FILE_L_ERROR:
                session.delete(requirement_file)
                session.commit()
            else:
                vprint(2, "Python File already processed")
                continue

        try:
            vprint(2, "Loading requirement {}".format(name))

            with open(str(repository.path / name), "rb") as ofile:
                content = ofile.read()

            if len(content) == 0:
                raise ValueError("is empty")

            coding = chardet.detect(content)
            if coding["encoding"] is None:
                raise TypeError("codec not detected")

            try:
                content = content.decode(coding['encoding'])
            except Exception:
                raise TypeError("invalid codec")

            if '\0' in content:
                vprint(3, "found null byte in content. Replacing it by \\n")
                content = content.replace("\0", "\n")

            requirement_file = RequirementFile(
                repository_id=repository.id,
                name=name,
                reqformat=reqformat,
                content=content,
                state=REQ_FILE_LOADED,
            )
            session.add(requirement_file)
        except ValueError as err:
            vprint(1, "Requirement {} {!r}".format(name, err))
            requirement_file = RequirementFile(
                repository_id=repository.id,
                name=name,
                reqformat=reqformat,
                state=REQ_FILE_EMPTY,
            )
            session.add(requirement_file)

        except Exception as err:
            vprint(1, "Failed to load requirement {} due {!r}".format(name, err))

            requirement_file = RequirementFile(
                repository_id=repository.id,
                name=name,
                reqformat=reqformat,
                state=REQ_FILE_L_ERROR,
            )
            session.add(requirement_file)


def process_repository(session, repository):
    """ Processes repository """

    if repository.state == REP_REQ_FILE_EXTRACTED \
            or repository.state in REP_ERRORS\
            or repository.state in states_after(REP_REQ_FILE_EXTRACTED, REP_ORDER):
        return "already processed"
    elif repository.state in states_before(REP_PF_EXTRACTED, REP_ORDER):
        return f'wrong script order, before you must run {states_before(REP_PF_EXTRACTED, REP_ORDER)}'

    setups, requirements, pipfiles, pipfile_locks = find_requirements(session, repository)

    if repository.state is not REP_UNAVAILABLE_FILES:
        process_requirement_files(session, repository, setups, "setup.py")
        process_requirement_files(session, repository, requirements, "requirements.txt")
        process_requirement_files(session, repository, pipfiles, "Pipfile")
        process_requirement_files(session, repository, pipfile_locks, "Pipfile.lock")
        repository.state = REP_REQ_FILE_EXTRACTED
    else:
        vprint(3, f"files are unavailable for repository {repository}, fix it then rerun all scripts.")

    session.add(repository)
    session.commit()
    return "done"


def main():
    """ Main function """
    script_name = os.path.basename(__file__)[:-3]

    parser = argparse.ArgumentParser(description="Extract requirement files from registered repositories")
    parser = set_up_argument_parser(parser, script_name)
    args = parser.parse_args()

    config.VERBOSE = args.verbose
    status = None

    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    with connect() as session, savepid():
        apply(
            session=session,
            status=status,
            selected_repositories=args.repositories or True,
            retry=True if args.retry_errors else False,
            count=args.count,
            interval=args.interval,
            reverse=args.reverse,
            check=set(args.check),
            process_repository=process_repository,
            model_type="requirement files",
            params=2
        )


if __name__ == "__main__":
    main()
