import os
import sys
src_path = os.path.dirname(os.path.abspath(''))
if src_path not in sys.path:
    sys.path.append(src_path)

import hashlib
import shutil
import subprocess
import pytz

from datetime import datetime
from src.config.states import REP_FILTERED


def extract_hash_parts(repo):
    """Extract hash parts from repo"""
    full_hash = hashlib.sha1(repo.encode("utf-8")).hexdigest()
    return full_hash[:2], full_hash[2:]


def git(*args):
    """Invoke git"""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.check_call(["git"] + list(args), env=env)


def git_output(*args, cwd=None):
    """Invoke git command and return output"""
    return subprocess.check_output(["git"] + list(args), cwd=cwd)


def format_commit(line, commit_type):
    try:
        commit_datetime, commit_hash, author, message = line.split('$_$', 3)
        commit_datetime = datetime.strptime(commit_datetime, "%Y-%m-%d %H:%M:%S %z")
        commit_datetime = commit_datetime.astimezone(pytz.timezone('GMT'))
        commit_row = {
            "repository_id": None,
            "type": commit_type,
            "hash": commit_hash,
            "date": commit_datetime,
            "author": author,
            "message": message
        }
        return commit_row
    except Exception:
        raise EnvironmentError("Invalid commit.")


def remove_repo_and_prepare(session, repository):
    if repository.dir_path:
        shutil.rmtree(str(repository.dir_path), ignore_errors=True)
    repository.state = REP_FILTERED
    session.commit()
    return repository.commit
