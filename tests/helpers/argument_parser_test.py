import argparse
import pytest
from src.helpers.h3_script_helpers import set_up_argument_parser


@pytest.fixture
def parser():
    return argparse.ArgumentParser()


def test_verbose_argument(parser):
    set_up_argument_parser(parser, "test_script")
    args = parser.parse_args(["-v", "2"])
    assert args.verbose == 2


def test_retry_errors_argument(parser):
    set_up_argument_parser(parser, "test_script")
    args = parser.parse_args(["-e"])
    assert args.retry_errors == True


def test_count_argument(parser):
    set_up_argument_parser(parser, "test_script")
    args = parser.parse_args(["-c"])
    assert args.count == True


def test_reverse_argument(parser):
    set_up_argument_parser(parser, "test_script")
    args = parser.parse_args(["-r"])
    assert args.reverse is True


def test_interval_argument(parser):
    set_up_argument_parser(parser, "test_script")
    args = parser.parse_args(["-i", "10", "20"])
    assert args.interval == [10, 20]


def test_check_argument(parser):
    set_up_argument_parser(parser, "test_script")
    args = parser.parse_args(["--check", "my_script.py"])
    assert args.check == ["my_script.py"]


def test_repository_argument(parser):
    set_up_argument_parser(parser, "test_script", script_type="repository")
    args = parser.parse_args(["-n", "1", "2"])
    assert args.repositories == [1, 2]


def test_code_cells_argument(parser):
    set_up_argument_parser(parser, "test_script", script_type="code_cells")
    args = parser.parse_args(["-s", "-t", "-n", "3", "4"])
    assert args.retry_syntaxerrors == True
    assert args.retry_timeout == True
    assert args.notebooks == [3, 4]