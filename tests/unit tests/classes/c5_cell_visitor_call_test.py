import os
import sys

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import ast
from src.classes.c5_cell_visitor import CellVisitor
from src.classes.c4_local_checkers import PathLocalChecker


class TestCellVisitorNewDataIO:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    def test_new_data_io(self, monkeypatch):
        assert len(self.cell_visitor.data_ios) == 0
        line = 10
        type_ = "module"
        caller = 'pd'
        function_name = "read_excel"
        function_type = "Attribute"
        source = "example.xlsx"
        source_type = "Constant"
        self.cell_visitor.new_data_io(line, type_, caller,
                                      function_name, function_type,
                                      source, source_type)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (line, type_, caller,
                      function_name, function_type,
                      source, source_type)


class TestCellVisitorGetFunctionData:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    def test_get_function_data_name(self):
        function_name = "read_csv"
        source = "'data.csv'"
        node = ast.parse(f"{function_name}({source})")
        function = node.body[0].value.func

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        result_caller, result_function_name, result_function_result = self.cell_visitor.get_function_data(function)
        assert result_caller is None
        assert result_function_name == function_name
        assert result_function_result == ast.Name.__name__

    def test_get_function_data_attribute(self):
        caller = "pd"
        function_name = "read_csv"
        source = "'data.csv'"
        node = ast.parse(f"{caller}.{function_name}({source})")
        function = node.body[0].value.func

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        result_caller, result_function_name, result_function_result = self.cell_visitor.get_function_data(function)
        assert result_caller == caller
        assert result_function_name == function_name
        assert result_function_result == ast.Attribute.__name__

    def test_get_function_data_subscript(self):
        function_name = "readers[0]"
        source = "'data.csv'"
        text = f"{function_name}({source})"
        node = ast.parse(text)
        function = node.body[0].value.func

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        result_caller, result_function_name, result_function_result = self.cell_visitor.get_function_data(function)
        assert result_caller is None
        assert result_function_name == function_name
        assert result_function_result == ast.Subscript.__name__

    def test_get_function_data_other(self):
        caller = "pd"
        function_name = "read_csv"
        source = "x + y"

        node = ast.parse(f"{caller}.{function_name}({source})")
        function = node.body[0].value.func
        function.value = None

        result_caller, result_function_name, result_function_type \
            = self.cell_visitor.get_function_data(function)
        assert result_caller is None
        assert result_function_name is None
        assert result_function_type is ast.Attribute.__name__


class TestCellVisitorGetSourceData:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    def test_get_source_data(self):
        caller = "pd"
        function_name = "read_csv"
        source = "data.csv"

        node = ast.parse("{}.{}(\"{}\")".format(caller, function_name, source))
        args = node.body[0].value.args

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source == source

    def test_get_source_data_no_args(self):
        args = []

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source is None

    def test_get_source_data_more_args(self):
        caller = "pd"
        function_name = "read_sql"
        source = "'SELECT * FROM data'"
        other_arg = "conn"

        node = ast.parse(f"{caller}.{function_name}({source}, {other_arg})")
        args = node.body[0].value.args

        result_source, result_source_type = self.cell_visitor.get_source_data(args)
        assert result_source == source
        assert result_source_type == ast.Constant.__name__

    def test_get_source_data_name(self):
        caller = "pd"
        function_name = "read_json"
        source = "SOURCE"

        node = ast.parse("{}.{}({})".format(caller, function_name, source))
        args = node.body[0].value.args

        result_source, result_source_type = self.cell_visitor.get_source_data(args)
        assert result_source == source

    def test_get_source_data_subscript(self):
        caller = "pd"
        function_name = "read_xlsx"
        source = "sources[0]"

        node = ast.parse(f"{caller}.{function_name}({source})")
        args = node.body[0].value.args

        result_source, result_source_type = self.cell_visitor.get_source_data(args)
        assert result_source == source
        assert result_source_type == ast.Subscript.__name__

    def test_get_source_data_call(self):
        upper_function = "order"
        function_name = "read_csv"
        source = "'data.csv'"
        upper_source = f"{function_name}({source})"

        node = ast.parse(f"{upper_function}({upper_source})")
        args = node.body[0].value.args

        result_source, result_source_type = self.cell_visitor.get_source_data(args)
        assert result_source == upper_source
        assert result_source_type == ast.Call.__name__


class TestCellVisitorVisitCall:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    """ Input and Output """

    def test_visit_call_input_read(self):
        function_name = "read_excel"
        source = "'data.xlsx'"
        text = f"{function_name}({source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", None,
                      function_name, ast.Name.__name__,
                      source, ast.Constant.__name__)

    def test_visit_call_output_to(self):
        caller = "df"
        function_name = "to_csv"
        source = "'data.csv'"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "output", caller,
                      function_name, ast.Attribute.__name__,
                      source, ast.Constant.__name__)

    """ Function Type"""

    def test_visit_call_input_func_name(self):
        function_name = "read_csv"
        source = "'data.csv'"
        text = f"{function_name}({source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", None,
                      function_name, ast.Name.__name__,
                      source, ast.Constant.__name__)

    def test_visit_call_input_func_attribute(self):
        caller = "pd"
        function_name = "read_csv"
        source = "'data.csv'"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", caller,
                      function_name, ast.Attribute.__name__,
                      source, ast.Constant.__name__)

    def test_visit_call_input_func_subscript(self):
        function_name = "reads[0]"
        source = "'data.csv'"
        text = f"{function_name}({source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", None,
                      function_name, ast.Subscript.__name__,
                      source, ast.Constant.__name__)

    """ Source Type """

    def test_visit_call_input_src_constant(self):
        caller = "pd"
        function_name = "read_csv"
        source = "'data.csv'"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", caller,
                      function_name, ast.Attribute.__name__,
                      source, ast.Constant.__name__)

    def test_visit_call_input_src_name(self):
        caller = "pd"
        function_name = "read_csv"
        source = "SOURCE"
        text = f"{caller}.{function_name}({source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", caller,
                      function_name, ast.Attribute.__name__,
                      source, ast.Name.__name__)

    def test_visit_call_input_src_subscript(self):
        function_name = "reads_excel"
        source = "reads[0]"
        text = f"{function_name}({source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", None,
                      function_name, ast.Name.__name__,
                      source, ast.Subscript.__name__)

    def test_visit_call_input_src_call_inner(self):
        upper_function = "order"
        function_name = "reads_excel"
        source = "source.xlsx"
        text = f"{upper_function}({function_name}({source}))"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        assert len(self.cell_visitor.data_ios) == 1
        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", None,
                      function_name, ast.Name.__name__,
                      source, ast.Attribute.__name__)

    def test_visit_call_input_src_call_both(self):
        upper_function = "opens"
        function_name = "reads_excel"
        source = "source.xlsx"
        upper_source = f"{function_name}({source})"
        text = f"{upper_function}({upper_source})"
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 2

        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[0]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", None,
                      function_name, ast.Name.__name__,
                      source, ast.Attribute.__name__)

        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[1]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (1, "input", None,
                      upper_function, ast.Name.__name__,
                      upper_source, ast.Call.__name__)
