import ast
import sys
import os
src = os.path.dirname(os.path.abspath(''))
if src not in sys.path: sys.path.append(src)

from src.helpers.c2_cell_visitor import CellVisitor
from src.helpers.c1_checkers import PathLocalChecker


class TestCellVisitorNewModule:
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

class TestCellVisitorVisitImport:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)
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

class TestCellVisitorImportFrom:
    def setup_method(self):
        self.checker = PathLocalChecker("")
        self.cell_visitor = CellVisitor(self.checker)

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
