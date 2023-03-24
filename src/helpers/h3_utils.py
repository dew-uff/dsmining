""" Util functions """
from __future__ import print_function

import ast
from contextlib import contextmanager
from timeout_decorator import timeout, TimeoutError, timeout_decorator  # noqa: F401

from src import consts as consts
from src.classes.c5_cell_visitor import CellVisitor
from src.config import Path

import subprocess
import os
import fnmatch
import sys
import src.config as config


def ignore_surrogates(original):
    new = original.encode('utf8', 'ignore').decode('utf8', 'ignore')
    return new, new != original


def to_unicode(text):
    if isinstance(text, str):
        return text
    return bytes(text).decode("utf-8")


def ext_split(values, ext):
    split = values.split(ext + ";")
    result = []
    for i, name in enumerate(split):
        if i != len(split) - 1:
            result.append(name + ext)
        else:
            result.append(name)
    return result


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


def base_dir_exists(out=None, err=None):
    exists = True
    if config.MOUNT_BASE:
        try:
            exists = config.SELECTED_REPOS_FILE.exists()
        except OSError as e:
            if e.errno == 107 and config.UMOUNT_BASE:
                subprocess.call(
                    config.UMOUNT_BASE, shell=True, stdout=out, stderr=err
                )
            exists = config.SELECTED_REPOS_FILE.exists()
    return exists


@contextmanager
def mount_umount(out=None, err=None):
    try:
        if not base_dir_exists(out, err) and config.MOUNT_BASE:
            subprocess.call(
                config.MOUNT_BASE, shell=True, stdout=out, stderr=err
            )
        yield
    finally:
        if config.SELECTED_REPOS_FILE.exists() and config.UMOUNT_BASE:
            subprocess.call(
                config.UMOUNT_BASE, shell=True, stdout=out, stderr=err
            )


@contextmanager
def mount_basedir(out=None, err=None):
    if not base_dir_exists(out, err) and config.MOUNT_BASE:
        subprocess.call(
            config.MOUNT_BASE, shell=True, stdout=out, stderr=err
        )
    yield


def invoke(program, *args):
    """Invoke program"""
    return subprocess.check_call([program] + list(map(str, args)))


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
    except:
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


def unzip_repository(session, repository):
    """Process repository"""
    if not repository.path.exists():
        if not repository.zip_path.exists():
            repository.processed |= consts.R_UNAVAILABLE_FILES
            session.add(repository)
            return "Failed to load due <repository not found>"
        uncompressed = subprocess.call([
            "tar", "-xjf", str(repository.zip_path),
            "-C", str(repository.zip_path.parent)
        ])
        if uncompressed != 0:
            return "Extraction failed with code {}".format(uncompressed)
    if repository.processed & consts.R_COMPRESS_OK:
        repository.processed -= consts.R_COMPRESS_OK
        session.add(repository)

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


def broken_link(notebook_file, repository_id):
    import textwrap
    vprint(3, "Notebook is broken link. Use the following SQL to fix:")
    text = (textwrap.dedent("""\
                select notebooks_count, (char_length(newtext) - char_length(replace(newtext, '''', ''))), concat(
                    'update repositories ',
                    'set notebooks_count = ',
                    (char_length(newtext) - char_length(replace(newtext, ';', ''))) + 1,
                    ', notebooks = ''',
                    newtext,
                    ''' where id = ',
                    id,
                    ';'
                ) from (
                    select id, notebooks_count, replace(
                        replace(
                            replace(
                                notebooks,
                                '{0};', ''
                            ),
                            ';{0}', ''
                        ),
                        '''', ''''''
                    ) as newtext
                    from repositories where id = {1}
                ) as foo;
                """.format(notebook_file, repository_id)))
    text = " ".join(x.strip() for x in text.split("\n"))
    print(text)
