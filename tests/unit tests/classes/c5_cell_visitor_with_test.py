import os
import sys
src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import ast
from src.classes.c5_cell_visitor import CellVisitor
from src.classes.c4_local_checkers import PathLocalChecker


class TestCellVisitorVisitWith:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

    def test_visit_call_input_read(self):
        function_name = "open"
        source = "data.text"
        mode = "r"
        text = "with open(\"{}\", \"{}\") {} my_file:\n\tprint(my_file.read())".format(source, mode, "as")
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 1

        assert self.cell_visitor.data_ios[0] \
               == (1, None, function_name, ast.Name.__name__, source, mode)

    def test_visit_call_input_nested(self):
        function_name = "open"
        source = "data.text"
        mode = "wb+"
        nested_caller = "pd"
        nested_function = "read_excel"
        nested_source = "data.xlsx"

        text = "with {}(\"{}\", \"{}\") {} my_file:\n\tprint(my_file.read())\n\t{}.{}(\"{}\")\n"\
            .format(function_name, source, mode, "as", nested_caller, nested_function, nested_source)
        node = ast.parse(text)

        assert len(self.cell_visitor.data_ios) == 0
        self.cell_visitor.visit(node)
        assert len(self.cell_visitor.data_ios) == 2

        assert self.cell_visitor.data_ios[0]\
               == (1, None, function_name, ast.Name.__name__, source, mode)

        assert self.cell_visitor.data_ios[1] \
               == (3, nested_caller, nested_function, ast.Attribute.__name__, nested_source, None)
