import sys
import os
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import re
import ast
import astunparse
from contextlib import contextmanager
from collections import OrderedDict


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

        input_modes = ["r","rb"]
        output_modes = ["w","wb", "x", "xb", "a", "ab"]

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
        self.input_modes = set(input_modes)
        self.output_modes = set(output_modes)

        self.scope = None
        self.globals = set()
        self.nonlocals = set()

        self.ipython_features = []
        self.modules = []
        self.data_ios = []
        self.local_checker = local_checker

    def new_module(self, line, type_, name):
        """Insert new module"""
        self.modules.append((line, type_, name, self.local_checker.is_local(name)))

    def new_data_io(self, line, type_, module_name, function_name, source, source_type):
        """Insert new data input or output"""
        self.data_ios.append((line, type_, module_name, function_name, source, source_type))

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


    @staticmethod
    def get_function_data(function):
        function_name = function.attr
        value = function.value
        caller = None
        if isinstance(value, ast.Name):
            caller = value.id

        return caller, function_name

    @staticmethod
    def get_source_type(arguments):
        if len(arguments) >= 1:
            first_arg = arguments[0]
            source = astunparse.unparse(first_arg).replace('\n', '')
            source_type = str(type(first_arg))
            return source, source_type
        return None

    def visit_With(self, node):
        items = node.items
        if len(items) == 0 or not items[0].context_expr:
            return self.generic_visit(node)

        context = items[0].context_expr

        if not isinstance(context, ast.Call) or len(context.args) < 2:
            return self.generic_visit(node)

        source = astunparse.unparse(context.args[0]).replace('\n', '')
        source_type = str(type(context.args[0]))
        open_mode = astunparse.unparse(context.args[1]).replace("\n", "").replace("'", "")

        if not context.func or not context.func.id:
            return self.generic_visit(node)

        function_name = context.func.id
        if open_mode and function_name and source and source_type:
            if open_mode in self.input_modes:
                self.new_data_io(node.lineno, 'input', 'with', function_name, source, source_type)
            elif open_mode in self.output_modes:
                self.new_data_io(node.lineno, 'output', 'with', function_name, source, source_type)

        self.visit_children(node, node.body)

    def visit_Call(self, node):

        function = node.func
        arguments =  node.args

        if not isinstance(function, ast.Attribute):
            return self.generic_visit(node)

        caller, function_name = self.get_function_data(function)

        if not (caller and function_name):
            return self.generic_visit(node)

        if "read" in function_name:
            source, source_type = self.get_source_type(arguments)
            if not source or not source_type:
                return self.generic_visit(node)
            self.new_data_io(node.lineno, 'input', caller, function_name, source, source_type)

        if "to_" in function_name:
            source, source_type = self.get_source_type(arguments)
            if not source or not source_type:
                return self.generic_visit(node)
            self.new_data_io(node.lineno, 'output', caller, function_name, source, source_type)

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