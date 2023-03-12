import ast
import astunparse


class CellVisitor(ast.NodeVisitor):

    def __init__(self, local_checker):
        self.local_checker = local_checker

        self.input_modes = ["r","rb"]
        self.output_modes = ["w","wb", "x", "xb", "a", "ab"]
        self.input_functions_names = ["read","open"]
        self.output_functions_names = ["to_"]

        self.modules = []
        self.data_ios = []

    def new_module(self, line, type_, name):
        """Insert new module"""
        self.modules.append((line, type_, name,
                             self.local_checker.is_local(name)))


    def new_data_io(self, line, type_, caller,
                    function_name, function_type,
                    source, source_type):
        """Insert new data input or output"""
        self.data_ios.append((line, type_, caller,
                              function_name, function_type,
                              source, source_type))


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
            if isinstance(first_arg, ast.Call):
                """ Adds Data IO recursively """
                self.visit(first_arg)
            source = astunparse.unparse(first_arg).replace('\n', '')
            source_type = type(first_arg).__name__
            return source, source_type
        return None, None


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


    def visit_Call(self, node):
        function = node.func
        arguments =  node.args

        caller, function_name, function_type = self.get_function_data(function)
        source, source_type = self.get_source_data(arguments)

        if not (function_name and function_type and source and source_type):
            return
        elif any(word in function_name for word in self.input_functions_names):
            self.new_data_io(node.lineno, 'input', caller,
                             function_name, function_type,
                             source, source_type)
        elif any(word in function_name for word in self.output_functions_names):
            self.new_data_io(node.lineno, 'output', caller,
                             function_name, function_type,
                             source, source_type)
