import os
import sys
src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)

import ast
import pytest

from src.classes.c4_local_checkers import PathLocalChecker
from src.helpers.h3_utils import extract_features
from tests.database_config import connection, session  # noqa: F401


class TestExtractFeatures:
    def test_extract_features(self, session):
        text = "import pandas as pd\ndf=pd.read_excel('data.xlsx')"
        checker = PathLocalChecker("")
        modules, data_ios = extract_features(text, checker)

        assert modules[0] == (1, "import", "pandas", False)
        assert data_ios[0] == (2, 'input', 'pd', 'read_excel', 'Attribute', "'data.xlsx'", 'Constant')

    def test_extract_features_error(self, session, monkeypatch):
        text = "import pandas as pd\ndf=pd.read_excel('data.xlsx')"
        checker = PathLocalChecker("")

        def mock_parse(text_): raise ValueError  # noqa: F841

        monkeypatch.setattr(ast, 'parse', mock_parse)

        with pytest.raises(SyntaxError):
            extract_features(text, checker)

