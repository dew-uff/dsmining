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
        line = 10
        caller = 'pd'
        function_name = "read_excel"
        function_type = "Attribute"
        source = "example.xlsx"

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.new_data_io(line, caller, function_name, function_type, source, None)
        assert len(self.cell_visitor.data_ios) == 1

        result_line, result_caller, result_function_name,\
            result_function_type, result_source, result_mode = self.cell_visitor.data_ios[0]

        assert (result_line, result_caller, result_function_name,
                result_function_type, result_source, result_mode)\
               == (line, caller, function_name, function_type, source, None)


class TestCellVisitorGetFunctionData:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    def test_get_function_data_name(self):
        function_name = "read_csv"
        source = "'data.csv'"
        node = ast.parse("{}({})".format(function_name, source))
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
        node = ast.parse("{}.{}({})".format(caller, function_name, source))
        function = node.body[0].value.func

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)

        result_caller, result_function_name, result_function_result = self.cell_visitor.get_function_data(function)
        assert result_caller == caller
        assert result_function_name == function_name
        assert result_function_result == ast.Attribute.__name__

    def test_get_function_data_subscript(self):
        function_name = "readers[0]"
        source = "data.csv"
        text = "{}(\"{}\")".format(function_name, source)
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

        node = ast.parse("{}.{}({})".format(caller, function_name, source))
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
        assert result_source == [source]

    def test_get_source_data_not_text(self):
        caller = "pd"
        function_name = "read_csv"
        source = "2"

        node = ast.parse("{}.{}({})".format(caller, function_name, source))
        args = node.body[0].value.args

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source == []

    def test_get_source_data_no_args(self):
        args = []

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source == []

    def test_get_source_data_more_args(self):
        caller = "pd"
        function_name = "read_csv"
        source = "source.csv"
        other_arg = "separator=':'"

        node = ast.parse("{}.{}('{}', {})"
                         .format(caller, function_name, source, other_arg))
        args = node.body[0].value.args

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source == [source]

    def test_get_source_data_more_text_args(self):
        caller = "pd"
        function_name = "read_csv"
        source = "source.csv"
        source2 = "source2.csv"

        node = ast.parse("{}.{}('{}', '{}')"
                         .format(caller, function_name, source, source2))
        args = node.body[0].value.args

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source == [source, source2]

    def test_get_source_data_variable(self):
        file = "data.json"
        caller = "pd"
        function_name = "read_json"
        source = "SOURCE"

        self.cell_visitor.variables[source] = file
        node = ast.parse("{} = {}\n{}.{}({})".format(source, file, caller, function_name, source))
        args = node.body[1].value.args

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source == [file]

    def test_get_source_data_subscript(self):
        caller = "pd"
        function_name = "read_xlsx"
        source = "sources[0]"

        node = ast.parse("{}.{}({})".format(caller, function_name, source))
        args = node.body[0].value.args

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source == []

    def test_get_source_data_call(self):
        outter_function = "order"
        function_name = "read_csv"
        source = "data.csv"
        outter_source = "{}('{}')".format(function_name, source)

        node = ast.parse("{}({})".format(outter_function, outter_source))
        args = node.body[0].value.args

        result_source = self.cell_visitor.get_source_data(args)
        assert result_source == []
        assert self.cell_visitor.data_ios[0] == (1, None, function_name, ast.Name.__name__, source, None)


class TestCellVisitorVisitCall:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    """ Function Type"""

    def test_visit_call_func_ast_name(self):
        function_name = "read_csv"
        source = "data.csv"
        text = "{}(\"{}\")".format(function_name, source)

        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 1

        assert self.cell_visitor.data_ios[0] \
               == (1, None, function_name, ast.Name.__name__, source, None)
        assert self.cell_visitor.extracted_args == 1
        assert self.cell_visitor.missed_args == 0

    def test_visit_call_func_ast_attribute(self):
        caller = "pd"
        function_name = "read_csv"
        source = "data.csv"
        text = "{}.{}(\"{}\")".format(caller, function_name, source)
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 1

        assert self.cell_visitor.data_ios[0] \
               == (1, caller, function_name, ast.Attribute.__name__, source, None)
        assert self.cell_visitor.extracted_args == 1
        assert self.cell_visitor.missed_args == 0

    def test_visit_call_input_func_ast_subscript(self):
        function_name = "reads[0]"
        source = "data.csv"
        text = "{}(\"{}\")".format(function_name, source)
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 1

        assert self.cell_visitor.data_ios[0] \
               == (1, None, function_name, ast.Subscript.__name__, source, None)
        assert self.cell_visitor.extracted_args == 1
        assert self.cell_visitor.missed_args == 0

    """ Source Type """

    def test_visit_call_text(self):
        function_name = "read_excel"
        source = "data.xlsx"
        text = "{}(\"{}\")".format(function_name, source)
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 1

        assert self.cell_visitor.data_ios[0] \
               == (1, None, function_name, ast.Name.__name__, source, None)
        assert self.cell_visitor.extracted_args == 1
        assert self.cell_visitor.missed_args == 0

    def test_visit_call_two_texts(self):
        function_name = "read_excel"
        source = "data.xlsx"
        source2 = "data2.xlsx"
        text = "{}(\"{}\", \"{}\")".format(function_name, source, source2)
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 2

        assert self.cell_visitor.data_ios[0] \
               == (1, None, function_name, ast.Name.__name__, source, None)
        assert self.cell_visitor.data_ios[1] \
               == (1, None, function_name, ast.Name.__name__, source2, None)
        assert self.cell_visitor.extracted_args == 2
        assert self.cell_visitor.missed_args == 0

    def test_visit_call_text_not_like_a_file(self):
        function_name = "read_excel"
        source = "data"
        text = "{}(\"{}\")".format(function_name, source)
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 0
        assert self.cell_visitor.extracted_args == 0
        assert self.cell_visitor.missed_args == 1

    def test_visit_call_variable(self):
        file = "data.csv"
        caller = "pd"
        function_name = "read_csv"
        source = "file"

        node = ast.parse("{}=\"{}\"\n{}.{}({})".format(source, file, caller, function_name, source))

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 1

        assert self.cell_visitor.data_ios[0] \
               == (2, caller, function_name, ast.Attribute.__name__, file, None)
        assert self.cell_visitor.extracted_args == 1
        assert self.cell_visitor.missed_args == 0

    def test_visit_call_variable_not_found(self):
        caller = "pd"
        function_name = "read_csv"
        source = "file"

        node = ast.parse("{}.{}({})".format(caller, function_name, source))

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 0
        assert self.cell_visitor.extracted_args == 0
        assert self.cell_visitor.missed_args == 1

    def test_visit_call_variable_not_text(self):
        file = "2"
        caller = "pd"
        function_name = "read_csv"
        source = "file"

        node = ast.parse("{}={}\n{}.{}({})".format(source, file, caller, function_name, source))

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 0
        assert self.cell_visitor.extracted_args == 0
        assert self.cell_visitor.missed_args == 1

    def test_visit_call_constant(self):
        file = "data.csv"
        caller = "pd"
        function_name = "read_csv"
        source = "FILE"

        node = ast.parse("{}=\"{}\"\n{}.{}({})".format(source, file, caller, function_name, source))

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 1

        assert self.cell_visitor.data_ios[0] \
               == (2, caller, function_name, ast.Attribute.__name__, file, None)

        assert self.cell_visitor.extracted_args == 1
        assert self.cell_visitor.missed_args == 0

    def test_visit_call_input_src_subscript(self):
        function_name = "reads_excel"
        source = "reads[0]"
        text = "{}({})".format(function_name, source)
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 0

        assert self.cell_visitor.extracted_args == 0
        assert self.cell_visitor.missed_args == 1

    def test_visit_call_input_src_call_inner(self):
        outter_function = "order"
        function_name = "reads_excel"
        source = "source.xlsx"
        text = "{}({}(\"{}\"))".format(outter_function, function_name, source)
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 1

        assert self.cell_visitor.data_ios[0]\
               == (1, None, function_name, ast.Name.__name__, source, None)

        assert self.cell_visitor.extracted_args == 2
        assert self.cell_visitor.missed_args == 0
