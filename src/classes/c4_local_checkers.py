import sys
import os
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path:
    sys.path.append(src)

from src.helpers.h3_utils import to_unicode


class PathLocalChecker(object):
    """ Checks module locality by looking at the directory """

    def __init__(self, path):
        path = to_unicode(path)
        self.base = os.path.dirname(path)

    def exists(self, path):
        return os.path.exists(path)

    def is_local(self, module):
        """ Checks if its package exists. """
        if module.startswith("."):
            return True
        path = self.base
        for part in module.split("."):
            path = os.path.join(path, part)
            if not self.exists(path) and not self.exists(path + u".py"):
                return False
        return True


class CompressedLocalChecker(PathLocalChecker):
    """ Checks module locality by looking at the zip file. """

    def __init__(self, tarzip, notebook_path):
        path = to_unicode(notebook_path)
        self.base = os.path.dirname(path)
        self.tarzip = tarzip

    def exists(self, path):
        try:
            self.tarzip.getmember(path)
            return True
        except KeyError:
            return False
