import ast
import sys
import os
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

from src.helpers.c2_cell_visitor import CellVisitor
from src.helpers.c1_checkers import PathLocalChecker


class TestCellVisitorVisitWith:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    def test_visit_call_input_read(self):
        function_name = "open"
        source = "'data.text'"
        text = f"with {function_name}({source}):\n" \
               f"\tcontents = print(f)\n" \
               f"\tf.read()"
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

    def test_visit_call_input_nested(self):
        function_name = "open"
        source = "'data.text'"
        nested_caller = "pd"
        nested_function = "read_excel"
        nested_source = "'data.xlsx'"
        text = f"with {function_name}({source}):\n" \
               f"\tcontents = print(f)\n" \
               f"\t{nested_caller}.{nested_function}({nested_source})"
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
                      source, ast.Constant.__name__)

        result_line, result_type, result_caller, \
            result_function_name, result_function_type, \
            result_source, result_source_type = self.cell_visitor.data_ios[1]
        assert (result_line, result_type, result_caller,
                result_function_name, result_function_type,
                result_source, result_source_type
                ) == (3, "input", nested_caller,
                      nested_function, ast.Attribute.__name__,
                      nested_source, ast.Constant.__name__)