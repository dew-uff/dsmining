""" Util functions """
from __future__ import print_function

import os
import re
import sys
import ast
import bisect
import fnmatch
import subprocess
import src.config as config

from src.config import Path
from contextlib import contextmanager
from src.classes.c5_cell_visitor import CellVisitor
from timeout_decorator import timeout, TimeoutError, timeout_decorator  # noqa: F401


def to_unicode(text):
    if isinstance(text, str):
        return text
    return bytes(text).decode("utf-8")


def vprint(verbose, *args):
    if config.VERBOSE > verbose:
        if verbose > 0:
            print(">" * verbose, *args)
        else:
            print(*args)


@contextmanager
def savepid():
    pid = None
    try:
        pid = os.getpid()
        with open("../.pid", "a") as fil:
            fil.write("{}\n".format(pid))
        yield pid
    finally:
        with open("../.pid", "r") as fil:
            pids = fil.readlines()

        with open("../.pid", "w") as fil:
            fil.write("\n".join(
                p.strip()
                for p in pids
                if p.strip()
                if int(p) != pid
            ) + "\n")


def find_files(path, pattern):
    """ Find files recursively """
    for root, _, filenames in os.walk(str(path)):
        for filename in fnmatch.filter(filenames, pattern):
            f = Path(root) / filename
            new_name = str(f).encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
            f.rename(new_name)
            yield Path(new_name)


def find_names(names, pattern, fn=Path):
    """Find path names in pattern"""
    for name in fnmatch.filter(names, pattern):
        yield fn(name)


def find_files_in_path(full_dir, patterns):
    """Find files in a path using patterns"""
    full_dir = str(full_dir)
    return [
        [
            file.relative_to(full_dir)
            for file in find_files(full_dir, "*" + pattern)
            if file.name == pattern
        ] for pattern in patterns
    ]


def _target(queue, function, *args, **kwargs):
    """Run a function with arguments and return output via a queue.
    This is a helper function for the Process created in _Timeout. It runs
    the function with positional arguments and keyword arguments and then
    returns the function's output by way of a queue. If an exception gets
    raised, it is returned to _Timeout that raises it by the value property.
    """
    try:
        queue.put((True, function(*args, **kwargs)))
    except:  # noqa
        # traceback.print_exc()
        queue.put((False, sys.exc_info()[1]))


def check_exit(matches):
    path = Path(".exit")
    if path.exists():
        with open(".exit", "r") as f:
            content = set(f.read().strip().split())
            if not content or content == {""}:
                return True
            return matches & content
    return False


timeout_decorator._target = _target


def unzip_repository(repository):
    """Process repository"""
    if not repository.path.exists():
        if not repository.zip_path.exists():
            return "Failed to load due <repository not found>"
        uncompressed = subprocess.call([
            "tar", "-xjf", str(repository.zip_path),
            "-C", str(repository.zip_path.parent)
        ])
        if uncompressed != 0:
            return "Extraction failed with code {}".format(uncompressed)
    return "done"


@timeout(1 * 60, use_signals=False)
def extract_features(text, checker):
    """Use cell visitor to extract features from cell text"""
    visitor = CellVisitor(checker)
    try:
        parsed = ast.parse(text)
    except ValueError:
        raise SyntaxError("Invalid escape")
    visitor.visit(parsed)

    return visitor.modules, visitor.data_ios


def cell_output_formats(cell):
    """Generates output formats from code cells"""
    if cell.get("cell_type") != "code":
        return
    for output in cell.get("outputs", []):
        if output.get("output_type") in {"display_data", "execute_result"}:
            for data_type in output.get("data", []):
                yield data_type
        elif output.get("output_type") == "error":
            yield "error"


def version_string_to_list(version):
    """Split version"""
    return [
        int(x) for x in re.findall(r"(\d+)\.?(\d*)\.?(\d*)", version)[0]
        if x
    ]

def specific_match(versions, position=0):
    """Matches a specific position in a trie dict ordered by its keys
    Recurse on the trie until it finds an end node (i.e. a non dict node)
    Position = 0 indicates it will follow the first element
    Position = -1 indicates it will follow the last element
    """
    if not isinstance(versions, dict):
        return versions
    keys = sorted(list(versions.keys()))
    return specific_match(versions[keys[position]], position)


def best_match(version, versions):
    """Get the closest version in a versions trie that matches the version
    in a list format"""

    if not isinstance(versions, dict):
        return versions
    if not version:
        return specific_match(versions, -1)
    if version[0] in versions:
        return best_match(version[1:], versions[version[0]])
    keys = sorted(list(versions.keys()))
    index = bisect.bisect_right(keys, version[0])
    position = 0
    if index == len(keys):
        index -= 1
        position = -1
    return specific_match(versions[keys[index]], position)


def get_pyexec(version, versions):
    return str(
        config.ANACONDA_PATH / "envs"
        / best_match(version, versions)
        / "bin" / "python"
    )


def invoke(program, *args):
    """Invoke program"""
    return subprocess.check_call([program] + list(map(str, args)))
