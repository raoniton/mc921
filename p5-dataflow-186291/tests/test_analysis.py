import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest
import timeout_decorator

from mjc.mj_analysis import DataFlow
from mjc.mj_code import CodeGenerator
from mjc.mj_interpreter import MJIRInterpreter
from mjc.mj_parser import MJParser
from mjc.mj_sema import SemanticAnalyzer, SymbolTableBuilder

name = [
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
]


def resolve_test_files(test_name):
    input_file = test_name + ".in"
    expected_file = test_name + ".out"
    speedup_file = test_name + ".speedup"

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

    # get expected speedup file real path
    speedup_path = test_folder / Path(speedup_file)
    assert speedup_path.exists()

    return input_path, expected_path, speedup_path


@pytest.mark.timeout(30)
@pytest.mark.parametrize("test_name", name)
# capfd will capture the stdout/stderr outputs generated during the test
def test_analysis(test_name, capsys):
    input_path, expected_path, speedup_path = resolve_test_files(test_name)

    p = MJParser(debug=False)
    with open(input_path) as f_in, open(expected_path) as f_ex:
        ast = p.parse(f_in.read())
        global_symtab_builder = SymbolTableBuilder()
        global_symtab = global_symtab_builder.visit(ast)
        sema = SemanticAnalyzer(global_symtab=global_symtab)
        sema.visit(ast)
        gen = CodeGenerator(False)
        gen.visit(ast)
        gencode = gen.code
        ast.text = gen.text
        opt = DataFlow(False)
        opt.visit(ast)
        optcode = opt.code
        vm = MJIRInterpreter()
        with pytest.raises(SystemExit) as sys_error:
            vm.run(optcode)
        captured = capsys.readouterr()
        assert sys_error.value.code == 0
        expect = f_ex.read()

    with open(speedup_path) as f_sp:
        reference = f_sp.read().split()
    ref_opt = int(reference[4])
    assert captured.out == expect
    assert captured.err == ""
    assert (len(gencode) / len(optcode) > 1.1) or (len(optcode) <= ref_opt)


@timeout_decorator.timeout(30)
def run_with_timeout(optcode):
    vm = MJIRInterpreter()
    try:
        vm.run(optcode)
    except SystemExit as e:
        return e.code
    return None


@pytest.mark.timeout(30)
@pytest.mark.parametrize("test_name", name)
# capfd will capture the stdout/stderr outputs generated during the test
def test_bonus(test_name, capsys):
    input_path, expected_path, speedup_path = resolve_test_files(test_name)

    p = MJParser(debug=False)
    with open(input_path) as f_in, open(expected_path) as f_ex:
        ast = p.parse(f_in.read())
        global_symtab_builder = SymbolTableBuilder()
        global_symtab = global_symtab_builder.visit(ast)
        sema = SemanticAnalyzer(global_symtab=global_symtab)
        sema.visit(ast)
        gen = CodeGenerator(False)
        gen.visit(ast)
        gencode = gen.code
        ast.text = gen.text
        opt = DataFlow(False)
        opt.visit(ast)
        optcode = opt.code
        vm = MJIRInterpreter()
        with pytest.raises(SystemExit) as sys_error:
            vm.run(optcode)
        captured = capsys.readouterr()
        assert sys_error.value.code == 0
        expect = f_ex.read()
    assert captured.out == expect
    assert captured.err == ""

    with open(speedup_path) as f_sp:
        reference = f_sp.read().split()
    ref_opt = int(reference[4])
    ref_speedup = float(reference[6])
    assert len(optcode) != 0
    assert (round(len(gencode) / len(optcode), 2) > ref_speedup) or (
        len(optcode) <= ref_opt
    )


def speedup_points():
    total_grade = 0
    for test_name in name:
        input_path, expected_path, speedup_path = resolve_test_files(test_name)
        cap_stdout = io.StringIO()
        cap_stderr = io.StringIO()
        code_err = -1

        with redirect_stdout(cap_stdout), redirect_stderr(cap_stderr):
            try:
                p = MJParser(debug=False)
                with open(input_path) as f_in, open(expected_path) as f_ex:
                    ast = p.parse(f_in.read())
                    global_symtab_builder = SymbolTableBuilder()
                    global_symtab = global_symtab_builder.visit(ast)
                    sema = SemanticAnalyzer(global_symtab=global_symtab)
                    sema.visit(ast)
                    gen = CodeGenerator(False)
                    gen.visit(ast)
                    gencode = gen.code
                    ast.text = gen.text
                    opt = DataFlow(False)
                    opt.visit(ast)
                    optcode = opt.code
                    code_err = run_with_timeout(optcode)
                    expect = f_ex.read()
                with open(speedup_path) as f_sp:
                    reference = f_sp.read().split()
                    ref_opt = int(reference[4])
            except Exception:
                print("Test failed", test_name, 0.0)
                continue
        if (
            cap_stdout.getvalue() != expect
            or cap_stderr.getvalue() != ""
            or not ((len(gencode) / len(optcode) > 1.1) or (len(optcode) <= ref_opt))
            or code_err != 0
        ):
            print("Test failed", test_name, 0.0)
            continue

        with open(speedup_path) as f_sp:
            reference = f_sp.read().split()
        grade = 0
        ref_opt = int(reference[4])
        ref_speedup = float(reference[6])
        if len(optcode) != 0:
            grade = round(len(gencode) / len(optcode), 2)
            grade = 0.55 if (grade > ref_speedup or len(optcode) <= ref_opt) else 0.5
        print("{} {:.2f}".format(test_name, grade))
        total_grade += grade
    print("{} {:.2f}".format("[Total]", total_grade))


if __name__ == "__main__":
    speedup_points()
