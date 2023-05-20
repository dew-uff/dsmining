"""Load markdown features"""

import os
import sys
dir_path = os.path.dirname(os.path.dirname(os.path.abspath('')))
if dir_path not in sys.path:
    sys.path.append(dir_path)

import argparse
import src.config.consts as consts

from src.db.database import connect
from src.db.database import Module
from src.helpers.h2_script_helpers import set_up_argument_parser
from src.helpers.h3_utils import vprint, check_exit, savepid
from src.classes.c2_status_logger import StatusLogger
from src.helpers.h4_filters import filter_python_files
from src.helpers.h6_aggregation_helpers import calculate_modules, load_repository
from src.helpers.h6_aggregation_helpers import calculate_data_ios
from src.config.states import *

TYPE = "python_file"


def process_python_file(session, python_file):
    if python_file.state == PF_AGGREGATED \
            or python_file.state in PF_ERRORS:
        return "already processed"

    agg_modules = calculate_modules(python_file, TYPE)
    data_ios = calculate_data_ios(python_file, TYPE)

    session.add(Module(**agg_modules))
    session.add_all(data_ios)

    python_file.state = PF_AGGREGATED
    session.add(python_file)

    return "ok"


def apply(
    session, status, selected_repositories,
    count, interval, reverse, check
):
    """Extract code cell features"""

    query = filter_python_files(
        session=session, selected_python_files=False,
        selected_repositories=selected_repositories,
        count=count, interval=interval, reverse=reverse
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
        result = process_python_file(session, python_file)
        vprint(1, result)
        status.count += 1
    session.commit()


def main():
    """Main function"""
    script_name = os.path.basename(__file__)[:-3]
    parser = argparse.ArgumentParser(description="Aggregates features from Python Files")
    parser = set_up_argument_parser(parser, script_name)
    args = parser.parse_args()

    consts.VERBOSE = args.verbose
    status = None
    if not args.count:
        status = StatusLogger(script_name)
        status.report()

    with connect() as session, savepid():
        apply(
            session=session,
            status=status,
            selected_repositories=args.repositories,
            count=args.count,
            interval=args.interval,
            reverse=args.reverse,
            check=set(args.check)
        )


if __name__ == '__main__':
    main()
