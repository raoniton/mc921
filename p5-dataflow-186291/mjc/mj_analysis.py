import argparse
import pathlib
import sys
from typing import List, Tuple

import rich

from mjc.mj_ast import ClassDecl, Program
from mjc.mj_block import (
    CFG,
    BasicBlock,
    ConditionBlock,
    EmitBlocks,
    format_instruction,
)
from mjc.mj_code import CodeGenerator
from mjc.mj_interpreter import MJIRInterpreter
from mjc.mj_parser import MJParser
from mjc.mj_sema import NodeVisitor, SemanticAnalyzer, SymbolTableBuilder


class DataFlow(NodeVisitor):
    def __init__(self, viewcfg: bool):
        # flag to show the optimized control flow graph
        self.viewcfg: bool = viewcfg
        # list of code instructions after optimizations
        self.code: List[Tuple[str]] = []
        # TODO

    def show(self):
        _str = ""
        for _code in self.code:
            _str += format_instruction(_code) + "\n"
        rich.print(_str.strip())

    def visit_Program(self, node: Program):
        # First, save the global instructions on code member
        self.code = node.text[:]  # [:] to do a copy

        # Visit all class declaration in the program
        for class_decl in node.class_decls:
            self.visit(class_decl)

    def visit_ClassDecl(self, node: ClassDecl):
        bb = EmitBlocks()
        bb.visit(node.cfg)
        for _code in bb.code:
            if "class" in _code[0] or "field" in _code[0]:
                self.code.append(_code)

        for method_decl in node.method_decls:
            self.current_func = method_decl
            # start with Reach Definitions Analysis
            self.buildRD_blocks(method_decl.cfg)
            self.computeRD_gen_kill()
            self.computeRD_in_out()
            # and do constant propagation optimization
            self.constant_propagation()

            # after do live variable analysis
            self.buildLV_blocks(method_decl.cfg)
            self.computeLV_use_def()
            self.computeLV_in_out()
            # and do dead code elimination
            self.deadcode_elimination()

            # after that do cfg simplify (optional)
            self.short_circuit_jumps(method_decl.cfg)
            self.merge_blocks(method_decl.cfg)
            self.discard_unused_allocs(method_decl.cfg)

            # finally save optimized instructions in self.code
            self.appendOptimizedCode(method_decl.cfg)

        if self.viewcfg:
            for method_decl in node.method_decls:
                method_name = getattr(method_decl, "name", None)
                if method_name is not None:
                    method_name = method_name.name
                else:
                    method_name = "main"

                dot = CFG(f"@{node.name.name}.{method_name}.opt")
                dot.view(method_decl.cfg)

    # TODO: add dataflow analysis


def main():
    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file",
        help="Path to file to be used to generate MJIR. By default, this script runs the interpreter on the optimized MJIR \
              and shows the speedup obtained from comparing original MJIR with its optimized version.",
        type=str,
    )
    parser.add_argument(
        "--opt",
        help="Print optimized MJIR generated from input_file.",
        action="store_true",
    )
    parser.add_argument(
        "--opt-pp",
        help="Print optimized MJIR generated from input_file.",
        action="store_true",
    )
    parser.add_argument(
        "--speedup",
        help="Show speedup from comparing original MJIR with its optimized version.",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "-c",
        "--cfg",
        help="show the CFG of the optimized MJIR for each function in pdf format",
        action="store_true",
    )
    args = parser.parse_args()

    speedup = args.speedup
    print_opt_ir = args.opt
    print_opt_ir_pp = args.opt_pp
    create_cfg = args.cfg

    # get input path
    input_file = args.input_file
    input_path = pathlib.Path(input_file)

    # check if file exists
    if not input_path.exists():
        print("Input", input_path, "not found", file=sys.stderr)
        sys.exit(1)

    # set error function
    p = MJParser()
    # open file and parse it
    with open(input_path) as f:
        ast = p.parse(f.read())

    global_symtab_builder = SymbolTableBuilder()
    global_symtab = global_symtab_builder.visit(ast)
    sema = SemanticAnalyzer(global_symtab=global_symtab)
    sema.visit(ast)

    gen = CodeGenerator(False)
    gen.visit(ast)
    gencode = gen.code
    ast.text = gen.text

    opt = DataFlow(create_cfg)
    opt.visit(ast)
    optcode = opt.code
    if print_opt_ir:
        print("Optimized MJIR: --------")
        rich.print(optcode)
        print("------------------------\n")

    elif print_opt_ir_pp:
        print("Optimized MJIR: --------")
        opt.show()
        print("------------------------\n")

    speedup = len(gencode) / len(optcode)
    sys.stderr.write(
        "[SPEEDUP] Default: %d Optimized: %d Speedup: %.2f\n\n"
        % (len(gencode), len(optcode), speedup)
    )

    if not (print_opt_ir or print_opt_ir_pp):
        vm = MJIRInterpreter()
        vm.run(optcode)


if __name__ == "__main__":
    main()
