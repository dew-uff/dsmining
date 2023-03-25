import argparse
import pytest
from src.helpers.h2_script_helpers import set_up_argument_parser


class TestArgumentParser:
    @pytest.fixture
    def parser(self):
        return argparse.ArgumentParser()

    def test_verbose_argument(self, parser):
        set_up_argument_parser(parser, "test_script")
        args = parser.parse_args(["-v", "2"])
        assert args.verbose == 2

    def test_retry_errors_argument(self, parser):
        set_up_argument_parser(parser, "test_script")
        args = parser.parse_args(["-e"])
        assert args.retry_errors is True

    def test_count_argument(self, parser):
        set_up_argument_parser(parser, "test_script")
        args = parser.parse_args(["-c"])
        assert args.count is True

    def test_reverse_argument(self, parser):
        set_up_argument_parser(parser, "test_script")
        args = parser.parse_args(["-r"])
        assert args.reverse is True

    def test_interval_argument(self, parser):
        set_up_argument_parser(parser, "test_script")
        args = parser.parse_args(["-i", "10", "20"])
        assert args.interval == [10, 20]

    def test_check_argument(self, parser):
        set_up_argument_parser(parser, "test_script")
        args = parser.parse_args(["--check", "my_script.py"])
        assert args.check == ["my_script.py"]

    def test_repository_argument(self, parser):
        set_up_argument_parser(parser, "test_script", script_type="repository")
        args = parser.parse_args(["-sr", "1", "2"])
        assert args.repositories == [1, 2]

    def test_code_cells_argument(self, parser):
        set_up_argument_parser(parser, "test_script", script_type="code_cells")
        args = parser.parse_args(["-s", "-t", "-sr", "3", "4"])
        assert args.retry_syntaxerrors is True
        assert args.retry_timeout is True
        assert args.repositories == [3, 4]
