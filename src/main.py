"""Main script that calls the others"""
import argparse
import subprocess
import smtplib
import sys
import os
from datetime import datetime


import src.config as config
from src.config import EXTRACTION_DIR
from src.helpers.h1_utils import StatusLogger, mount_basedir, check_exit, savepid

ORDER = [
    "e1_notebooks_and_cells",
    "e2_python_files",
    "e3_requirement_files",
    "e4_markdown_cells",
    "e5_code_cells",
    "e6_python_files",
    "e7_compress",
    "e8_extract_files",
    "p1_notebook_aggregate",
    "p2_python_aggregate"
]


def execute_script(script, args):
    """ Execute script and save log """
    moment = datetime.now().strftime("%Y%m%dT%H%M%S")
    print("[{}] Executing {}.py".format(moment, script))
    out = config.LOGS_DIR / ("{}-{}.outerr".format(script, moment))
    if out.exists():
        out = str(out) + ".2"
    with open(str(out), "wb") as outf:
        options = ['python', '-u', EXTRACTION_DIR +os.sep + script + ".py"] + args
        status = subprocess.call(options, stdout=outf, stderr=outf)
        print("> Status", status)
        return status


def main():
    """Main function"""
    with savepid():
        scripts = sys.argv[1:]

        result = []

        try:
            # with mount_basedir():
            #     config.BASE_DIR.mkdir(parents=True, exist_ok=True)
            # config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

            indexes = [
                index
                for index, name in enumerate(scripts)
                if name == "--all"
                or config.Path(name).exists()
                or config.Path(name + ".py").exists()
            ]
            indexes.sort()
            indexes.append(None)
            it_indexes= iter(indexes)
            next(it_indexes)
            to_execute = {
                scripts[cur]: scripts[cur + 1:nex]
                for cur, nex in zip(indexes, it_indexes)
            }
            options_to_all = []
            if "--all" in to_execute:
                options_to_all = to_execute["--all"]
                del to_execute["--all"]

            if not to_execute:
                to_execute = {
                    script: []
                    for script in ORDER
                }

            for script, args in to_execute.items():
                if check_exit({"all", "main", "main.py"}):
                    print("Found .exit file. Exiting")
                    return
                if script.endswith(".py"):
                    script = script[:-3]
                args = args + options_to_all
                status = execute_script(script, args)
                result.append("{} {} --> {}".format(script, " ".join(args), status))
            print("done")
        finally:
            status = StatusLogger("main closed")
            status.report()


if __name__ == "__main__":
    main()
