"""Load python files"""
import argparse
import os
import config
import consts

from src.db.database import PythonFile, Repository, connect
from h1_utils import vprint, StatusLogger, check_exit, savepid, find_files, mount_basedir


def find_python_files(session, repository):
    """Finds all python files in the repository but setup.py"""
    python_files = [
        str(file.relative_to(repository.path))
        for file in find_files(repository.path, "*.py")
        if "/setup.py" not in str(file) and str(file) != 'setup.py'
    ]
    return python_files


def process_repository(session, repository, skip_if_error=consts.R_P_ERROR):
    """Process repository"""
    if repository.processed & (consts.R_P_EXTRACTION + skip_if_error):
        return "already processed"
    if repository.processed & skip_if_error:
        session.add(repository)
        repository.processed -= skip_if_error

    finished = True

    count = 0
    repository_python_files_names = find_python_files(session, repository)

    for name in repository_python_files_names:
        if not name:
            continue

        count += 1

        python_file = session.query(PythonFile).filter(
            PythonFile.repository_id == repository.id,
            PythonFile.name == name,
        ).first()

        if python_file is not None:
            if python_file.processed & consts.PF_ERROR:
                session.delete(python_file)
                session.commit()

        vprint(3, "Loading python file {}".format(name))

        file_path = str(repository.path) + os.sep + name

        with open(file_path) as f:
            source = f.read()

        python_file = PythonFile(
            repository_id=repository.id,
            name=name,
            source=source,
            total_lines=len(open(file_path).readlines()),
            processed=consts.PF_OK
        )
        session.add(python_file)


    if finished and not repository.processed & skip_if_error:
        repository.processed |= consts.R_P_EXTRACTION
        repository.python_files_count = count
        session.add(repository)
        session.commit()
    return "done"


def apply(
        session, status, selected_repositories, skip_if_error,
        count, interval, reverse, check
):
    while selected_repositories:
        filters = [
            Repository.processed.op("&")(consts.R_P_EXTRACTION) == 0,
            Repository.processed.op("&")(skip_if_error) == 0,
        ]
        if selected_repositories is not True:
            filters += [
                Repository.id.in_(selected_repositories[:30])
            ]
            selected_repositories = selected_repositories[30:]
        else:
            selected_repositories = False
            if interval:
                filters += [
                    Repository.id >= interval[0],
                    Repository.id <= interval[1],
                ]
        query = session.query(Repository).filter(*filters)
        if count:
            print(query.count())
            return

        if reverse:
            query = query.order_by(
                Repository.id.desc()
            )
        else:
            query = query.order_by(
                Repository.id.asc()
            )

        for repository in query:
            if check_exit(check):
                vprint(0, "Found .exit file. Exiting")
                return
            status.report()
            vprint(0, "Extracting python files from {}".format(repository))
            with mount_basedir():
                result = process_repository(
                    session,
                    repository,
                    skip_if_error
                )
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
            0 if args.retry_errors else consts.R_P_ERROR,
            args.count,
            args.interval,
            args.reverse,
            set(args.check)
        )


if __name__ == "__main__":
    main()
