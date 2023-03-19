""" Extracts Requirement Files from repositories """
import os
import argparse
import chardet
import src.config as config
import src.consts as consts

from src.db.database import RequirementFile, connect
from src.helpers.h1_utils import vprint, StatusLogger, check_exit, savepid, unzip_repository
from src.helpers.h1_utils import find_files_in_path, mount_basedir
from src.helpers.h3_script_helpers import filter_repositories


def find_requirements(session, repository):
    setups, requirements, pipfiles, pipfile_locks = [], [], [], []

    if not repository.path.exists():
        msg = unzip_repository(session, repository)
        if msg != "done":
            vprint(2, "repository not found")
            repository.processed |= consts.R_UNAVAILABLE_FILES
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


def process_requirement_files(session, repository, req_names, reqformat,
                              skip_if_error=consts.R_REQUIREMENTS_ERROR):
    """ Processes a requirement file """
    no_errors = True

    if not repository.path.exists():
        vprint(2, "Unzipping repository: {}".format(repository.zip_path))
        msg = unzip_repository(session, repository)
        if msg != "done":
            vprint(2, msg)
            no_errors = False
            return no_errors

    for item in req_names:
        name = str(item)
        if not name:
            continue

        requirement_file = session.query(RequirementFile).filter(
            RequirementFile.repository_id == repository.id,
            RequirementFile.name == name,
        ).first()

        if requirement_file is not None:
            if requirement_file.processed & consts.R_REQUIREMENTS_ERROR:
                session.delete(requirement_file)
                session.commit()

        try:
            vprint(2, "Loading requirement {}".format(name))

            with open(str(repository.path / name), "rb") as ofile:
                content = ofile.read()

            coding = chardet.detect(content)
            if coding["encoding"] is None:
                raise ValueError("Codec not detected")

            try:
                content = content.decode(coding['encoding'])
            except Exception:
                raise ValueError("Invalid codec")

            if '\0' in content:
                vprint(3, "Found null byte in content. Replacing it by \\n")
                content = content.replace("\0", "\n")

            requirement_file = RequirementFile(
                repository_id=repository.id,
                name=name,
                reqformat=reqformat,
                content=content,
                processed=consts.F_OK,
            )
            session.add(requirement_file)

        except Exception as err:
            vprint(1, "Failed to load requirement {} due {!r}".format(name, err))
            # We mark this python file as broken and keep adding the rest.
            requirement_file = RequirementFile(
                repository_id=repository.id,
                name=name,
                reqformat=reqformat,
                processed=consts.F_ERROR,
            )
            session.add(requirement_file)

    return no_errors


def process_repository(session, repository, skip_if_error=consts.R_REQUIREMENTS_ERROR):
    """ Processes repository """
    if repository.processed & (consts.R_REQUIREMENTS_OK + skip_if_error):
        return "already processed"

    if repository.processed & consts.R_REQUIREMENTS_ERROR:
        session.add(repository)
        vprint(3, "retrying to process {}".format(repository))
        repository.processed -= consts.R_REQUIREMENTS_ERROR

    no_error = True

    setups, requirements, pipfiles, pipfile_locks = find_requirements(session, repository)

    no_error &= process_requirement_files(session, repository, setups, "setup.py")
    no_error &= process_requirement_files(session, repository, requirements, "requirements.txt")
    no_error &= process_requirement_files(session, repository, pipfiles, "Pipfile")
    no_error &= process_requirement_files(session, repository, pipfile_locks, "Pipfile.lock")

    if no_error:
        repository.processed |= consts.R_REQUIREMENTS_OK
    else:
        repository.processed |= consts.R_REQUIREMENTS_ERROR

    session.add(repository)
    session.commit()
    return "done"


def apply(
        session, status, selected_repositories, skip_if_error,
        count, interval, reverse, check
):
    while selected_repositories:

        selected_repositories, query = filter_repositories(
            session=session, selected_repositories=selected_repositories,
            skip_if_error=skip_if_error, count=count,
            interval=interval, reverse=reverse,
            skip_already_processed=consts.R_REQUIREMENTS_OK)

        for repository in query:
            if check_exit(check):
                vprint(0, "Found .exit file. Exiting")
                return
            status.report()
            vprint(0, "Extracting requirement files from {}".format(repository))
            with mount_basedir():
                result = process_repository(session, repository, skip_if_error)
                vprint(1, result)
            status.count += 1
            session.commit()


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(
        description="Extract requirement files from registered repositories")
    parser.add_argument("-v", "--verbose", type=int, default=config.VERBOSE,
                        help="increase output verbosity")
    parser.add_argument("-n", "--repositories", type=int, default=None,
                        nargs="*",
                        help="repositories ids")
    parser.add_argument("-i", "--interval", type=int, nargs=2,
                        default=config.REPOSITORY_INTERVAL,
                        help="id interval")
    parser.add_argument("-e", "--retry-errors", action='store_true',
                        help="retry errors")
    parser.add_argument("-c", "--count", action='store_true',
                        help="count results")
    parser.add_argument('-r', '--reverse', action='store_true',
                        help='iterate in reverse order')
    parser.add_argument('--check', type=str, nargs='*',
                        default={'all', script_name, script_name + '.py'},
                        help='check name in .exit')

    args = parser.parse_args()
    config.VERBOSE = args.verbose
    status = None
    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    with connect() as session, savepid():
        apply(
            session,
            status,
            args.repositories or True,
            0 if args.retry_errors else consts.R_REQUIREMENTS_ERROR,
            args.count,
            args.interval,
            args.reverse,
            set(args.check)
        )


if __name__ == "__main__":
    main()
