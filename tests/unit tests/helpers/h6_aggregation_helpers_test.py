import os
import sys

from src.helpers.h6_aggregation_helpers import infer_source

src = os.path.dirname(os.path.dirname(os.path.abspath(''))) + '/src'
if src not in sys.path:
    sys.path.append(src)


class TestAggregationHelpers:
    def test_infer_source_file(self):
        text = "data.csv"
        infered_source_type, infered_file, infered_file_extension = infer_source(text)
        assert infered_source_type == "file"
        assert infered_file == "data"
        assert infered_file_extension == "csv"

    def test_infer_source_website(self):
        text = "https://www.youtube.com/"
        infered_source_type, infered_file, infered_file_extension = infer_source(text)
        assert infered_source_type == "website"
        assert infered_file is None
        assert infered_file_extension is None

    def test_infer_source_email(self):
        text = "test@gmail.com"
        infered_source_type, infered_file, infered_file_extension = infer_source(text)
        assert infered_source_type == "email"
        assert infered_file is None
        assert infered_file_extension is None
