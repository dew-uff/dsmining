import os
import re
import ast
import sys

from h1_utils import to_unicode, ignore_surrogates
from contextlib import contextmanager
from collections import Counter, OrderedDict, defaultdict


class PathLocalChecker(object):
    """Check if module is local by looking at the directory"""

    def __init__(self, path):
        path = to_unicode(path)
        self.base = os.path.dirname(path)

    def exists(self, path):
        return os.path.exists(path)

    def is_local(self, module):
        """Check if module is local by checking if its package exists"""
        if module.startswith("."):
            return True
        path = self.base
        for part in module.split("."):
            path = os.path.join(path, part)
            if not self.exists(path) and not self.exists(path + u".py"):
                return False
        return True


class SetLocalChecker(PathLocalChecker):
    """Check if module is local by looking at a set"""

    def __init__(self, dirset, notebook_path):
        path = to_unicode(notebook_path)
        self.base = os.path.dirname(path)
        self.dirset = dirset

    def exists(self, path):
        path, _ = ignore_surrogates(path)
        if path[0] == "/":
            path = path[1:]
        return path in self.dirset or (path + "/") in self.dirset


class CompressedLocalChecker(PathLocalChecker):
    """Check if module is local by looking at the zip file"""

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


class CellVisitor(ast.NodeVisitor):

    def __init__(self, local_checker):
        self.counter = OrderedDict()
        custom = [
            "import_star", "functions_with_decorators",
            "classes_with_decorators", "classes_with_bases",
            "delname", "delattr", "delitem",
            "assignname", "assignattr", "assignitem",
            "ipython", "ipython_superset",
            "ast_statements", "ast_expressions",
        ]
        scoped = [
            "importfrom", "import", "assign", "delete",
            "functiondef", "classdef"
        ]
        modules = [
            "module", "interactive", "expression", "suite"
        ]
        statements = [
            "functiondef", "asyncfunctiondef", "classdef", "return",
            "delete", "assign", "augassign", "annassign", "print",
            "for", "asyncfor", "while", "if", "with", "asyncwith",
            "raise", "try", "tryexcept", "tryfinally", "assert",
            "import", "importfrom", "exec", "global", "nonlocal", "expr",
            "pass", "break", "continue"
        ]
        expressions = [
            "boolop", "binop", "unaryop", "lambda", "ifexp",
            "dict", "set", "listcomp", "setcomp", "dictcomp", "generatorexp",
            "await", "yield", "yieldfrom",
            "compare", "call", "num", "str", "formattedvalue", "joinedstr",
            "bytes", "nameconstant", "ellipsis", "constant",
            "attribute", "subscript", "starred", "name", "list", "tuple",
        ]
        others = [
            "load", "store", "del", "augload", "augstore", "param",
            "slice", "index",
            "and", "or",
            "add", "sub", "mult", "matmult", "div", "mod", "pow", "lshift",
            "rshift", "bitor", "bitxor", "bitand", "floordiv",
            "invert", "not", "uadd", "usub",
            "eq", "noteq", "lt", "lte", "gt", "gte", "is", "isnot", "in", "notin",
            "comprehension", "excepthandler", "arguments", "arg",
            "keyword", "alias", "withitem",
        ]

        for nodetype in custom:
            self.counter[nodetype] = 0
        for nodetype in scoped:
            self.counter["class_" + nodetype] = 0
            self.counter["global_" + nodetype] = 0
            self.counter["nonlocal_" + nodetype] = 0
            self.counter["local_" + nodetype] = 0
            self.counter["total_" + nodetype] = 0
        for nodetype in modules:
            self.counter["ast_" + nodetype] = 0
        for nodetype in statements:
            self.counter["ast_" + nodetype] = 0
        for nodetype in expressions:
            self.counter["ast_" + nodetype] = 0
        for nodetype in others:
            self.counter["ast_" + nodetype] = 0
        # self.counter["------"] = 0
        self.counter["ast_others"] = ""

        self.statements = set(statements)
        self.expressions = set(expressions)

        self.scope = None
        self.globals = set()
        self.nonlocals = set()

        self.ipython_features = []
        self.modules = []
        self.local_checker = local_checker
        self.names = defaultdict(Counter)

    def new_module(self, line, type_, name):
        """Insert new module"""
        self.modules.append((line, type_, name, self.local_checker.is_local(name)))

    @contextmanager
    def set_scope(self, scope):
        old_scope = self.scope
        old_globals = self.globals
        old_nonlocals = self.nonlocals
        try:
            self.scope = scope
            self.globals = set()
            self.nonlocals = set()
            yield
        finally:
            self.scope = old_scope
            self.globals = old_globals
            self.nonlocals = old_nonlocals

    def count_simple(self, name):
        if name not in self.counter:
            self.counter["ast_others"] += name + " "
        else:
            self.counter[name] += 1

    def count(self, name, varname=None, scope=None):
        if varname in self.globals:
            scope = "global"
        if varname in self.nonlocals:
            scope = "nonlocal"
        scope = scope or self.scope
        if scope is not None:
            self.counter["{}_{}".format(scope, name)] += 1
        self.counter["total_{}".format(name)] += 1
        return scope

    def count_name(self, varname, mode, scope=None):
        if varname in self.globals:
            scope = "global"
        if varname in self.nonlocals:
            scope = "nonlocal"
        scope = scope or self.scope or "main"
        self.names[(scope, mode)][varname] += 1

    def count_targets(self, targets, name, sub_name):
        for target in targets:
            if isinstance(target, ast.Name):
                self.count_simple("{}name".format(sub_name))
                self.count(name, target.id)
            if isinstance(target, ast.Attribute):
                self.count_simple("{}attr".format(sub_name))
                self.count(name)
            if isinstance(target, ast.Subscript):
                self.count_simple("{}item".format(sub_name))
                self.count(name)
            if isinstance(target, (ast.List, ast.Tuple)):
                self.count_targets(target.elts, name, sub_name)

    def visit_children(self, node, *children):
        for child in children:
            child_node = getattr(node, child, None)
            if child_node:
                if isinstance(child_node, (list, tuple)):
                    for child_part in child_node:
                        self.visit(child_part)
                else:
                    self.visit(child_node)
        if not children:
            ast.NodeVisitor.generic_visit(self, node)

    def generic_visit(self, node):
        name = type(node).__name__.lower()
        self.count_simple("ast_" + name)
        if name in self.statements:
            self.count_simple("ast_statements")
        if name in self.expressions:
            self.count_simple("ast_expressions")
        self.visit_children(node)

    def visit_FunctionDef(self, node, simple="ast_functiondef"):
        self.count_name(node.name, "function")
        self.count_simple("ast_statements")
        self.count_simple(simple)
        self.count("functiondef", node.name)
        with self.set_scope("local"):
            self.visit_children(node, "body")

        if node.decorator_list:
            self.count_simple("functions_with_decorators")

        if sys.version_info < (3, 0):
            self.visit_children(node, "args", "decorator_list")
        else:
            self.visit_children(node, "args", "decorator_list", "returns")

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node, simple="ast_asyncfunctiondef")

    def visit_ClassDef(self, node):
        self.count_name(node.name, "class")
        self.count_simple("ast_statements")
        self.count_simple("ast_classdef")
        self.count("classdef", node.name)
        with self.set_scope("class"):
            self.visit_children(node, "body")

        if node.decorator_list:
            self.count_simple("classes_with_decorators")

        if any(
            base for base in node.bases
            if not isinstance(base, ast.Name)
            or not base.id == "object"
        ):
            self.count_simple("classes_with_bases")

        if sys.version_info < (3, 0):
            self.visit_children(node, "bases", "decorator_list")
        elif sys.version_info < (3, 5):
            self.visit_children(node, "bases", "keywords", "starargs", "kwargs", "decorator_list")
        else:
            self.visit_children(node, "bases", "keywords", "decorator_list")

    def visit_Delete(self, node):
        self.count_targets(node.targets, "delete", "del")
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.count_targets(node.targets, "assign", "assign")
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.count_targets([node.target], "assign", "assign")
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self.count_targets([node.target], "assign", "assign")
        self.generic_visit(node)

    def visit_For(self, node):
        self.count_targets([node.target], "assign", "assign")
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.visit_For(node)

    def visit_Import(self, node):
        """Get module from imports"""

        for import_ in node.names:
            self.new_module(node.lineno, "import", import_.name)
        for alias in node.names:
            name = alias.asname or alias.name
            self.count_name(name, "import")
            self.count("import", name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Get module from imports"""
        self.new_module(
            node.lineno, "import_from",
            ("." * (node.level or 0)) + (node.module or "")
        )
        for alias in node.names:
            name = alias.asname or alias.name
            self.count_name(name, "importfrom")
            if name == "*":
                self.count_simple("import_star")
            self.count("importfrom", name)
        self.generic_visit(node)

    def visit_Global(self, node):
        self.globals.update(node.names)
        self.generic_visit(node)

    def visit_Nonlocal(self, node):
        self.nonlocals.update(node.names)
        self.generic_visit(node)

    def visit_Call(self, node):
        """get_ipython().<method> calls"""

        func = node.func
        if not isinstance(func, ast.Attribute):
            return self.generic_visit(node)
        value = func.value
        if not isinstance(value, ast.Call):
            return self.generic_visit(node)
        value_func = value.func
        if not isinstance(value_func, ast.Name):
            return self.generic_visit(node)
        if value_func.id != "get_ipython":
            return self.generic_visit(node)
        args = node.args
        if not args:
            return self.generic_visit(node)
        if not isinstance(args[0], ast.Str):
            return self.generic_visit(node)
        if not args[0].s:
            return self.generic_visit(node)

        self.count_simple("ipython_superset")

        type_ = func.attr
        split = args[0].s.split()
        name, = split[0:1] or ['']

        self.ipython_features.append((node.lineno, node.col_offset, type_, name))

        if name == "load_ext":
            try:
                module = split[1] if len(split) > 1 else args[1].s
            except IndexError:
                return
            self.new_module(node.lineno, "load_ext", module)

    def visit_Subscript(self, node):
        """Collect In, Out, _oh, _ih"""
        self.generic_visit(node)
        if not isinstance(node.value, ast.Name):
            return
        if node.value.id in {"In", "_ih"}:
            type_ = "input_ref"
        elif node.value.id in {"Out", "_oh"}:
            type_ = "output_ref"
        else:
            return
        self.count_simple("ipython")
        self.ipython_features.append((node.lineno, node.col_offset, type_, node.value.id + "[]"))

    def visit_Name(self, node):
        """Collect _, __, ___, _i, _ii, _iii, _0, _1, _i0, _i1, ..., _sh"""
        self.count_name(node.id, type(node.ctx).__name__.lower())
        self.generic_visit(node)
        type_ = None
        underscore_num = re.findall(r"(^_(i)?\d*$)", node.id)
        many_underscores = re.findall(r"(^_{1,3}$)", node.id)
        many_is = re.findall(r"(^_i{1,3}$)", node.id)
        if underscore_num:
            type_ = "input_ref" if underscore_num[0][1] else "output_ref"
        elif many_underscores:
            type_ = "output_ref"
        elif many_is:
            type_ = "input_ref"
        elif node.id == "_sh":
            type_ = "shadown_ref"

        if type_ is not None:
            self.count_simple("ipython")
            self.ipython_features.append((node.lineno, node.col_offset, type_, node.id))