import ast
import re

import astunparse


class CellVisitor(ast.NodeVisitor):

    def __init__(self, local_checker):
        self.local_checker = local_checker
        self.variables = {}
        self.modules = []
        self.data_ios = []

    def new_module(self, line, type_, name):
        """Insert new module"""
        self.modules.append((line, type_, name, self.local_checker.is_local(name)))

    def new_data_io(self, line, caller, function_name, function_type, source):
        """Insert new data input or output"""
        self.data_ios.append((line, caller, function_name, function_type, source))

    @staticmethod
    def get_function_data(function):
        caller = None
        function_name = None
        function_type = type(function).__name__

        if isinstance(function, ast.Name):
            function_name = function.id
        elif isinstance(function, ast.Attribute):
            if isinstance(function.value, ast.Name) and \
                    isinstance(function.attr, str):
                caller = function.value.id
                function_name = function.attr
        elif isinstance(function, ast.Subscript):
            function_name = astunparse.unparse(function).replace('\n', '')

        return caller, function_name, function_type

    def get_source_data(self, arguments):
        if len(arguments) >= 1:
            first_arg = arguments[0]
            value = None

            if isinstance(first_arg, ast.Constant):
                value = self.visit(first_arg)

            elif isinstance(first_arg, ast.Name):
                value = self.variables.get(first_arg.id, None)

            elif isinstance(first_arg, ast.Call):
                """ Adds Data IO recursively """
                value = self.visit(first_arg)

            if value and (isinstance(value, ast.Str) or isinstance(value, str)):
                return value

        return None

    @staticmethod
    def like_a_file(string):
        re.match(r"^.+\.[a-z]+$", string)

    def visit_Str(self, node):
        return node.value

    def visit_Assign(self, node):
        target = node.targets[0]
        if isinstance(target, ast.Name):
            varname = target.id
            value = self.visit(node.value)

            if varname and value and isinstance(value, str):
                self.variables[varname] = value

    def visit_Call(self, node):
        function = node.func
        arguments = node.args

        caller, function_name, function_type = self.get_function_data(function)

        if function_name and function_type:
            source = self.get_source_data(arguments)

            if source and self.like_a_file(source):
                self.new_data_io(node.lineno, caller, function_name, function_type, source)

    def visit_Import(self, node):
        """ Gets modules from 'import ...' """
        for import_ in node.names:
            self.new_module(node.lineno, "import", import_.name)

    def visit_ImportFrom(self, node):
        """ Gets module from "from ...import ...' """
        self.new_module(
            node.lineno, "import_from",
            ("." * (node.level or 0)) + (node.module or "")
        )
