import sys
from pathlib import Path

import pytest

from mjc.mj_lexer import MJLexer


def resolve_test_files(test_name):
    input_file = test_name + ".in"
    expected_file = test_name + ".out"

    # get current dir
    current_dir = Path(__file__).parent.absolute()

    # get absolute path to inputs folder
    test_folder = current_dir / Path("in-out")

    # get input path and check if exists
    input_path = test_folder / Path(input_file)
    assert input_path.exists()

    # get expected test file real path
    expected_path = test_folder / Path(expected_file)
    assert expected_path.exists()

    return input_path, expected_path


@pytest.mark.parametrize(
    "test_name",
    [
        "t01",
        "t02",
        "t03",
        "t04",
        "t05",
        "t06",
        "t07",
        "t08",
        "t09",
        "t10",
        "t11",
        "t12",
        "t13",
        "t14",
        "t15",
        "t16",
        "t17",
        "t18",
        "t19",
        "t20",
    ],
)
# capfd will capture the stdout/stderr outputs generated during the test
def test_lexer(test_name, capfd):
    input_path, expected_path = resolve_test_files(test_name)

    def print_error(msg, x, y):
        # use stdout to compare the outputs corretly with pytest
        print("Lexical error: %s at %d:%d" % (msg, x, y), file=sys.stdout)

    lexer = MJLexer(print_error)
    with open(input_path) as f_in, open(expected_path) as f_ex:
        lexer.scan(f_in.read())
        captured = capfd.readouterr()
        expect = f_ex.read()
    assert captured.out == expect
