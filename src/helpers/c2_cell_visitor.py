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

        input_modes = ["r","rb"]
        output_modes = ["w","wb", "x", "xb", "a", "ab"]
        self.input_modes = set(input_modes)
        self.output_modes = set(output_modes)


        self.modules = []
        self.data_ios = []
        self.local_checker = local_checker


    def new_module(self, line, type_, name):
        """Insert new module"""
        self.modules.append((line, type_, name, self.local_checker.is_local(name)))


    def new_data_io(self, line, type_, module_name, function_name, source, source_type):
        """Insert new data input or output"""
        self.data_ios.append((line, type_, module_name, function_name, source, source_type))


    @staticmethod
    def get_function_data(function):
        if isinstance(function.value, ast.Name) and\
                isinstance(function.attr, str):
            caller = function.value.id
            function_name = function.attr
            return caller, function_name
        return None, None


    @staticmethod
    def get_source_type(arguments):
        if len(arguments) >= 1:
            first_arg = arguments[0]
            source = astunparse.unparse(first_arg).replace('\n', '')
            source_type = str(type(first_arg))
            return source, source_type
        return None, None



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
            ast.NodeVisitor.visit_children(self, node)


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


    def visit_With(self, node):
        items = node.items
        if len(items) == 0 or not items[0].context_expr:
            return self.visit_children(node)

        context = items[0].context_expr

        if not isinstance(context, ast.Call) or len(context.args) < 2:
            return self.visit_children(node)

        source = astunparse.unparse(context.args[0]).replace('\n', '')
        source_type = str(type(context.args[0]))
        open_mode = astunparse.unparse(context.args[1]).replace("\n", "").replace("'", "")

        if not context.func or not context.func.id:
            return self.visit_children(node)

        function_name = context.func.id
        if open_mode and function_name and source and source_type:
            if open_mode in self.input_modes:
                self.new_data_io(node.lineno, 'input', 'with', function_name, source, source_type)
            elif open_mode in self.output_modes:
                self.new_data_io(node.lineno, 'output', 'with', function_name, source, source_type)

        # self.visit_children(node, node.body)

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
