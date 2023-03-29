import os
import sys
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path:
    sys.path.append(src)

from src import config
from src.helpers.h4_filters import filter_repositories
from src.helpers.h3_utils import vprint, check_exit


def set_up_argument_parser(parser, script_name, script_type="repository"):
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        type=int, default=config.VERBOSE)
    parser.add_argument("-e", "--retry-errors", help="retry errors",
                        action="store_true")
    parser.add_argument("-c", "--count", help="count filtered repositories",
                        action="store_true")
    parser.add_argument("-r", "--reverse", help="iterate in reverse order",
                        action="store_true")
    parser.add_argument("-i", "--interval", help="interval",
                        type=int, nargs=2, default=config.REPOSITORY_INTERVAL)
    parser.add_argument("--check", help="check name in .exit", type=str,
                        nargs="*", default={"all", script_name, script_name + ".py"})
    parser.add_argument("-sr", "--repositories", help="selected repositories ids",
                        type=int, default=None, nargs="*")

    if script_type == "code_cells" or script_type == "python_files":
        parser.add_argument('-s', '--retry-syntaxerrors', help='retry syntax errors',
                            action='store_true')
        parser.add_argument('-t', '--retry-timeout', help='retry timeout',
                            action='store_true')

    return parser


def apply(session, status, selected_repositories, retry,
          count, interval, reverse, check,
          process_repository, model_type, params=3):

    query = filter_repositories(
        session=session,
        selected_repositories=selected_repositories,
        count=count,
        interval=interval, reverse=reverse
    )

    for repository in query:
        if check_exit(check):
            vprint(0, "Found .exit file. Exiting")
            return
        status.report()
        vprint(0, "Extracting {} from {}".format(model_type, repository))

        result = ''
        if params == 3:
            result = process_repository(session, repository, retry)
        elif params == 2:
            result = process_repository(session, repository)
        vprint(0, result)

        status.count += 1
        session.commit()


