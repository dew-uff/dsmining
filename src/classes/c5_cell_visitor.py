import ast
import re
import astunparse
import sys

class CellVisitor(ast.NodeVisitor):

    def __init__(self, local_checker):
        self.local_checker = local_checker
        self.variables = {}
        self.modules = []
        self.data_ios = []
        self.extracted_args = 0
        self.missed_args = 0

    def new_module(self, line, type_, name):
        """Insert new module"""
        self.modules.append((line, type_, name, self.local_checker.is_local(name)))

    def new_data_io(self, line, caller, function_name, function_type, source, mode):
        """Insert new data input or output"""
        self.extracted_args = self.extracted_args + 1
        self.data_ios.append((line, caller, function_name, function_type, source, mode))

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

    def get_file_open_mode(self, mode_arg):
        modes = [
            "r", "w", "x", "a",
            "rb", "wb", "xb", "ab",
            "rt", "wt", "xt", "at",
            "r+", "w+", "x+", "a+",
            "rb+", "wb+", "xb+", "ab+",
            "rt+", "wt+", "xt+", "at+",
        ]

        value = self.visit(mode_arg)
        if value and (isinstance(value, ast.Str) or isinstance(value, str)) and value in modes:
            return value

    def get_argument_data(self, arg, sources):
        value = None

        if sys.version_info.major > 3 and isinstance(arg, ast.Constant):
            value = self.visit(arg)

        elif isinstance(arg, ast.Name):
            value = self.variables.get(arg.id, None)

        elif isinstance(arg, ast.Call):
            """ Adds Data IO recursively """
            self.extracted_args = self.extracted_args + 1
            self.visit(arg)
            return sources

        if value and (isinstance(value, ast.Str) or isinstance(value, str)):
            sources.append(value)
        else:
            self.missed_args = self.missed_args + 1

        return sources

    def get_source_data(self, arguments):
        sources = []
        if len(arguments) >= 1:
            for arg in arguments:
                sources = self.get_argument_data(arg, sources)
        return sources

    def get_open_data(self, arguments):
        sources = []
        if len(arguments) >= 2 and isinstance(arguments[1], ast.Constant):
            source_arg = arguments[0]
            mode_arg = arguments[1]

            sources = self.get_argument_data(source_arg, sources)
            mode = self.get_file_open_mode(mode_arg)

            if sources and mode:
                return sources, mode

        return self.get_source_data(arguments), None

    @staticmethod
    def like_a_file(string):
        return bool(re.match(r"^.+\.[a-z]+$", string))

    def visit_Str(self, node):
        return astunparse.unparse(node).replace('\n', '').replace('\'', '').replace('"', '')

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
            mode = None
            if function_name == "open":
                sources, mode = self.get_open_data(arguments)
            else:
                sources = self.get_source_data(arguments)

            for src in sources:
                if self.like_a_file(src):
                    self.new_data_io(node.lineno, caller, function_name, function_type, src, mode)
                else:
                    self.missed_args = self.missed_args + 1

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
