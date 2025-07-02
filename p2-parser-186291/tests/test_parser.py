import re
import sys
from pathlib import Path

import pytest

from mjc.mj_parser import MJParser


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


def get_conflit_counters(parser_log):
    # Patterns to search
    sr_conflit_pattern = r"WARNING:\s*(\d+)\s*shift/reduce"
    rr_conflit_pattern = r"WARNING:\s*(\d+)\s*reduce/reduce"

    # Search the patters in the parser log
    sr_match = re.search(sr_conflit_pattern, parser_log)
    rr_match = re.search(rr_conflit_pattern, parser_log)

    # Get the conflit counters
    sr_count = int(sr_match.group(1)) if sr_match else 0
    rr_count = int(rr_match.group(1)) if rr_match else 0

    return sr_count, rr_count


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
        "t22",
        "t24",
        "t25",
        "t26",
        "t28",
        "t29",
        "t31",
        "t32",
        "t33",
        "t34",
        "t35",
        "t36",
        "t38",
        "t39",
        "t40",
    ],
)
# capsys will capture the stdout/stderr outputs generated during the test
def test_parser(test_name, capsys):
    input_path, expected_path = resolve_test_files(test_name)

    parser = MJParser(debug=False)
    with open(input_path) as f_in, open(expected_path) as f_ex:
        ast = parser.parse(f_in.read())
        # pytest fails to substitute sys.stdout if not passed here
        ast.show(buf=sys.stdout, showcoord=True)
        captured = capsys.readouterr()
        expect = f_ex.read()
    assert captured.out == expect
    assert captured.err == ""


@pytest.mark.parametrize("test_name", ["t21", "t23", "t27", "t30", "t37"])
# capsys will capture the stdout/stderr outputs generated during the test
def test_parser_error(test_name, capsys):
    input_path, expected_path = resolve_test_files(test_name)

    parser = MJParser(debug=False)
    with open(input_path) as f_in, open(expected_path) as f_ex:
        with pytest.raises(SystemExit) as sys_error:
            ast = parser.parse(f_in.read())
            ast.show(showcoord=True)
        assert sys_error.value.code == 1
        captured = capsys.readouterr()
        expect = f_ex.read()
        assert captured.out == expect
        assert captured.err == ""


@pytest.mark.parametrize("test_name", ["t41"])
# capsys will capture the stdout/stderr outputs generated during the test
def test_parser_conflicts(test_name, capsys):
    input_path, expected_path = resolve_test_files(test_name)

    p = MJParser(debug=False)
    with open(input_path) as f_in, open(expected_path) as f_ex:
        ast = p.parse(f_in.read())
        # pytest fails to substitute sys.stdout if not passed here
        ast.show(buf=sys.stdout, showcoord=True)
        captured = capsys.readouterr()
        expect = f_ex.read()
    assert captured.out == expect
    assert captured.err == ""

    # The number of shift/reduce and reduce/reduce conflicts must be <= 1
    sr_count, rr_count = get_conflit_counters(p.log.text)
    assert sr_count <= 1 and rr_count == 0
