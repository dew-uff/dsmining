import sys
import os
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

import ast
from src.helpers.c2_cell_visitor import CellVisitor
from src.helpers.c1_checkers import PathLocalChecker


class TestCellVisitorImports:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    def test_new_module_local(self, monkeypatch):
        assert len(self.cell_visitor.modules) == 0

        line = 10
        type_ = "module"
        name = "test_module"
        monkeypatch.setattr(self.cell_visitor.local_checker, 'is_local', lambda *args, **kwargs: True)
        self.cell_visitor.new_module(line, type_, name)

        assert len(self.cell_visitor.modules) == 1
        result_line, result_type, result_name, result_local = self.cell_visitor.modules[0]
        assert (result_line, result_type, result_name, result_local) == (line, type_, name, True)

    def test_new_module_external(self, monkeypatch):
        assert len(self.cell_visitor.modules) == 0

        line = 10
        type_ = "module"
        name = "test_module"
        monkeypatch.setattr(self.cell_visitor.local_checker, 'is_local', lambda *args, **kwargs: False)
        self.cell_visitor.new_module(line, type_, name)

        assert len(self.cell_visitor.modules) == 1
        result_line, result_type, result_name, result_local = self.cell_visitor.modules[0]
        assert (result_line, result_type, result_name, result_local) == (line, type_, name, False)

    def test_visit_import_local(self, monkeypatch):
        name = "src.utils"
        text = f"import {name}"
        node =  ast.parse(text)
        monkeypatch.setattr(self.cell_visitor.local_checker, 'is_local', lambda *args, **kwargs: True)

        assert len(self.cell_visitor.modules) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.modules) == 1
        result_line, result_type, result_name, result_local = self.cell_visitor.modules[0]
        assert (result_line, result_type, result_name, result_local) == (1, 'import', name, True)

    def test_visit_import_external(self, monkeypatch):
        name = "matplotlib"
        text = f"import {name}"
        node =  ast.parse(text)
        monkeypatch.setattr(self.cell_visitor.local_checker, 'is_local', lambda *args, **kwargs: False)

        assert len(self.cell_visitor.modules) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.modules) == 1

        result_line, result_type, result_name, result_local = self.cell_visitor.modules[0]
        assert (result_line, result_type, result_name, result_local) == (1, 'import', name, False)

    def test_visit_import_two_lines(self, monkeypatch):
        name1, name2 = "src.utils", "matplotlib"
        text = f"import {name1}\nimport {name2}"
        node =  ast.parse(text)
        monkeypatch.setattr(self.cell_visitor.local_checker, 'is_local', lambda *args, **kwargs: True)

        assert len(self.cell_visitor.modules) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.modules) == 2
        result_line1, result_type1, result_name1, result_local1 = self.cell_visitor.modules[0]
        assert (result_line1, result_type1, result_name1, result_local1) == (1, 'import', name1, True)
        result_line2, result_type2, result_name2, result_local2 = self.cell_visitor.modules[1]
        assert (result_line2, result_type2, result_name2, result_local2) == (2, 'import', name2, True)

    def test_visit_import_two_imports(self, monkeypatch):
        name1, name2 = "sys", "os"
        text = f"import {name1}, {name2}"
        node =  ast.parse(text)
        monkeypatch.setattr(self.cell_visitor.local_checker, 'is_local', lambda *args, **kwargs: True)

        assert len(self.cell_visitor.modules) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.modules) == 2
        result_line1, result_type1, result_name1, result_local1 = self.cell_visitor.modules[0]
        assert (result_line1, result_type1, result_name1, result_local1) == (1, 'import', name1, True)
        result_line2, result_type2, result_name2, result_local2 = self.cell_visitor.modules[1]
        assert (result_line2, result_type2, result_name2, result_local2) == (1, 'import', name2, True)


    # vist_ImportFrom

    def test_visit_import_from_local(self, monkeypatch):
        module, name = "matplotlib", "pyplot"
        text = f"from {module} import {name}"
        node =  ast.parse(text)
        monkeypatch.setattr(self.cell_visitor.local_checker, 'is_local', lambda *args, **kwargs: True)

        assert len(self.cell_visitor.modules) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.modules) == 1
        result_line, result_type, result_name, result_local = self.cell_visitor.modules[0]
        assert (result_line, result_type, result_name, result_local) == (1, 'import_from', module, True)

    def test_visit_import_from_external(self, monkeypatch):
        module, name = "matplotlib", "pyplot"
        text = f"from {module} import {name}"
        node = ast.parse(text)
        monkeypatch.setattr(self.cell_visitor.local_checker, 'is_local', lambda *args, **kwargs: False)

        assert len(self.cell_visitor.modules) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.modules) == 1
        result_line, result_type, result_name, result_local = self.cell_visitor.modules[0]
        assert (result_line, result_type, result_name, result_local) == (1, 'import_from', module, False)

    def test_visit_import_from_levels(self, monkeypatch):
        levels = 2
        module, name = "helpers", "get_python_version"
        text = f"from {'.' * levels}{module} import {name}"
        node =  ast.parse(text)
        monkeypatch.setattr(self.cell_visitor.local_checker,
                            'is_local', lambda *args, **kwargs: True)

        assert len(self.cell_visitor.modules) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.modules) == 1
        result_line, result_type,result_name, result_local = self.cell_visitor.modules[0]
        assert (result_line, result_type, result_name, result_local
                ) == (1, 'import_from', ('.' * levels) + module, True)


class TestCellVisitorVisitCall:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    def test_new_data_io(self, monkeypatch):
        assert len(self.cell_visitor.data_ios) == 0
        line = 10
        type_ = "module"
        module_name = 'pd'
        function_name = "read_excel"
        source = "example.xlsx"
        source_type = "Constant"
        self.cell_visitor.new_data_io(line, type_, module_name, function_name, source, source_type)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, \
            result_module_name, result_function_name, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type,
                result_module_name, result_function_name,
                result_source, result_source_type
                ) == (line, type_, module_name, function_name, source, source_type)

    def test_get_function_data(self):
        caller = "pd"
        function_name = "read_csv"
        source = "'data.csv'"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)
        function = node.body[0].value.func

        result_caller, result_function_name = self.cell_visitor.get_function_data(function)
        assert result_caller == caller
        assert result_function_name == function_name

    def test_get_function_data_error(self):
        caller = "pd"
        function_name = "read_csv"
        source = ""

        node = ast.parse(f"{caller}.{function_name}({source})")
        function = node.body[0].value.func
        function.value = None

        result_caller, result_function_name = self.cell_visitor.get_function_data(function)
        assert result_caller is None
        assert result_function_name is None

    def test_get_source_type(self):
        caller = "pd"
        function_name = "read_csv"
        source = "'data.csv'"

        node = ast.parse(f"{caller}.{function_name}({source})")
        args = node.body[0].value.args

        result_source, result_source_type = self.cell_visitor.get_source_type(args)
        assert result_source == source
        assert result_source_type == str(ast.Constant)

    def test_get_source_type_no_args(self):
        args = []

        result_source, result_source_type = self.cell_visitor.get_source_type(args)
        assert result_source is None
        assert result_source_type is None

    def test_get_source_type_more_args(self):
        caller = "pd"
        function_name = "read_sql"
        source = "'SELECT * FROM data'"
        other_arg = "conn"

        node = ast.parse(f"{caller}.{function_name}({source}, {other_arg})")
        args = node.body[0].value.args

        result_source, result_source_type = self.cell_visitor.get_source_type(args)
        assert result_source == source
        assert result_source_type == str(ast.Constant)

    def test_get_source_type_name(self):
        caller = "pd"
        function_name = "read_json"
        source = "SOURCE"

        node = ast.parse(f"{caller}.{function_name}({source})")
        args = node.body[0].value.args

        result_source, result_source_type = self.cell_visitor.get_source_type(args)
        assert result_source == source
        assert result_source_type == str(ast.Name)

    def test_get_source_type_subscript(self):
        caller = "pd"
        function_name = "read_xlsx"
        source = "sources[0]"

        node = ast.parse(f"{caller}.{function_name}({source})")
        args = node.body[0].value.args

        result_source, result_source_type = self.cell_visitor.get_source_type(args)
        assert result_source == source
        assert result_source_type == str(ast.Subscript)

    def test_visit_call_input_read(self):
        caller = "pd"
        function_name = "read_csv"
        source = "'data.csv'"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)


        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, \
            result_module_name, result_function_name, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type,
                result_module_name, result_function_name,
                result_source, result_source_type
                ) == (1, "input", caller, function_name, source, str(ast.Constant))

    def test_visit_call_output_to(self):
        caller = "df"
        function_name = "to_csv"
        source = "'data.csv'"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)


        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, \
            result_module_name, result_function_name, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type,
                result_module_name, result_function_name,
                result_source, result_source_type
                ) == (1, "output", caller, function_name, source, str(ast.Constant))


    def test_visit_call_input_name(self):
        caller = "pd"
        function_name = "read_csv"
        source = "SOURCE"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)


        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, \
            result_module_name, result_function_name, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type,
                result_module_name, result_function_name,
                result_source, result_source_type
                ) == (1, "input", caller, function_name, source, str(ast.Name))


    def test_visit_call_input_subscript(self):
        caller = "pd"
        function_name = "read_csv"
        source = "sources[2]"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)


        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, \
            result_module_name, result_function_name, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type,
                result_module_name, result_function_name,
                result_source, result_source_type
                ) == (1, "input", caller, function_name, source, str(ast.Subscript))


    def test_visit_call_not_attribute(self):
        caller = "pd"
        function_name = "read_csv"
        source = "sources[2]"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)


        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, \
            result_module_name, result_function_name, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type,
                result_module_name, result_function_name,
                result_source, result_source_type
                ) == (1, "input", caller, function_name, source, str(ast.Subscript))
