"""Load markdown features"""
import argparse
import os
import src.config as config
import src.consts as consts

from src.db.database import PythonFile, connect
from src.db.database import Module
from src.helpers.h1_utils import vprint, StatusLogger, check_exit, savepid
from src.helpers.h4_aggregation_helpers import  calculate_modules

TYPE = "python_file"

def process_python_file(session, python_file, skip_if_error):
    if python_file.processed & consts.PF_AGGREGATE_ERROR:
        python_file.processed -= consts.PF_AGGREGATE_ERROR
        session.add(python_file)
    if python_file.processed & consts.PF_AGGREGATE_OK:
        return "already processed"


    syntax_error = bool(PythonFile.processed.op("&")(consts.PF_SYNTAX_ERROR) == consts.PF_SYNTAX_ERROR)

    if python_file.total_lines == 0:
        python_file.processed |= consts.PF_AGGREGATE_OK
        session.add(python_file)
        return "ok - empty python_file"

    if syntax_error:
        python_file.processed |= consts.PF_AGGREGATE_OK
        python_file.processed |= consts.PF_SYNTAX_ERROR
        session.add(python_file)
        return "ok - syntax error"

    agg_modules = calculate_modules(python_file, TYPE)

    session.add(Module(**agg_modules))
    python_file.processed |= consts.PF_AGGREGATE_OK
    session.add(python_file)

    return "ok"


def load_repository(session, python_file, repository_id):
    if repository_id != python_file.repository_id:
        try:
            session.commit()
        except Exception as err:
            vprint(0, 'Failed to save modules from repository {} due to {}'.format(
                repository_id, err
            ))

        vprint(0, 'Processing repository: {}'.format(repository_id))
        return python_file.repository_id

    return repository_id


def apply(
    session, status, skip_if_error,
    count, interval, reverse, check
):
    """Extract code cell features"""
    filters = [
        PythonFile.processed.op("&")(consts.PF_AGGREGATE_OK) == 0,
        PythonFile.processed.op("&")(skip_if_error) == 0,
    ]
    if interval:
        filters += [
            PythonFile.repository_id >= interval[0],
            PythonFile.repository_id <= interval[1],
        ]

    query = (
        session.query(PythonFile)
        .filter(*filters)
    )

    if count:
        print(query.count())
        return

    if reverse:
        query = query.order_by(
            PythonFile.repository_id.desc(),
            PythonFile.id.desc(),
        )
    else:
        query = query.order_by(
            PythonFile.repository_id.asc(),
            PythonFile.id.asc(),
        )

    repository_id = None

    for python_file in query:
        if check_exit(check):
            session.commit()
            vprint(0, 'Found .exit file. Exiting')
            return
        status.report()

        repository_id = load_repository(session, python_file, repository_id)

        vprint(1, 'Processing Python File: {}'.format(python_file))
        result = process_python_file(session, python_file, skip_if_error)
        vprint(1, result)
        status.count += 1
    session.commit()


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(
        description='Execute repositories')
    parser.add_argument('-v', '--verbose', type=int, default=config.VERBOSE,
                        help='increase output verbosity')
    parser.add_argument('-e', '--retry-errors', action='store_true',
                        help='retry errors')
    parser.add_argument('-i', '--interval', type=int, nargs=2,
                        default=config.REPOSITORY_INTERVAL,
                        help='repository id interval')
    parser.add_argument('-c', '--count', action='store_true',
                        help='count results')
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
            0 if args.retry_errors else consts.PF_AGGREGATE_ERROR,
            args.count,
            args.interval,
            args.reverse,
            set(args.check)
        )

if __name__ == '__main__':
    main()
