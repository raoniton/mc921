import argparse
import pathlib
import sys
from typing import Dict, List, Tuple

import rich

from mjc.mj_ast import *
from mjc.mj_block import (
    CFG,
    BasicBlock,
    Block,
    ConditionBlock,
    EmitBlocks,
    format_instruction,
)
from mjc.mj_interpreter import MJIRInterpreter
from mjc.mj_parser import MJParser
from mjc.mj_sema import NodeVisitor, SemanticAnalyzer, SymbolTableBuilder
from mjc.mj_type import CharType, IntType, VoidType


class CodeGenerator(NodeVisitor):
    """
    Node visitor class that creates 3-address encoded instruction sequences
    with Basic Blocks & Control Flow Graph.
    """

    def __init__(self, viewcfg: bool):
        self.viewcfg: bool = viewcfg
        self.current_block: Block = None

        # version dictionary for temporaries. We use the name as a Key
        self.fname: str = "_glob_"
        self.versions: Dict[str, int] = {self.fname: 0}

        # The generated code (list of tuples)
        # At the end of visit_program, we call each function definition to emit
        # the instructions inside basic blocks. The global instructions that
        # are stored in self.text are appended at beginning of the code
        self.code: List[Tuple[str]] = []

        # Used for global declarations & constants (list, strings)
        self.text: List[Tuple[str]] = []

        # TODO: Complete if needed.

    def show(self):
        _str = ""
        for _code in self.code:
            _str += format_instruction(_code) + "\n"
        rich.print(_str.strip())

    def new_temp(self) -> str:
        """
        Create a new temporary variable of a given scope (function name).
        """
        if self.fname not in self.versions:
            self.versions[self.fname] = 1
        name = "%" + "%d" % (self.versions[self.fname])
        self.versions[self.fname] += 1
        return name

    def new_text(self, typename: str) -> str:
        """
        Create a new literal constant on global section (text).
        """
        name = "@." + typename + "." + "%d" % (self.versions["_glob_"])
        self.versions["_glob_"] += 1
        return name

    # You must implement visit_Nodename methods for all of the AST nodes.
    # In your code, you will need to make instructions
    # and append them to the current block code list.
    #
    # A few sample methods follow. Do not hesitate to complete or change
    # them if needed.

    def visit_Program(self, node: Program):
        # First visit all of the Class Declarations
        for class_decl in node.class_decls:
            self.visit(class_decl)

        # At the end of codegen, first init the self.code with the list
        # of global instructions allocated in self.text
        self.code = self.text.copy()

        # After, visit all the class definitions and emit the
        # code stored inside basic blocks.
        for class_decl in node.class_decls:
            block_visitor = EmitBlocks()
            block_visitor.visit(class_decl.cfg)
            for code in block_visitor.code:
                self.code.append(code)

    def visit_ClassDecl(self, node: ClassDecl):
        # Create a cfg to hold the class context
        node.cfg = BasicBlock(label=None)

        #
        # Guideline
        #
        # Generate the class decl instruction
        # Visit all the Field Declarations
        # Visit all the Method Declarations
        # TODO: Complete.

        # Finally, visit all the method definitions and emit the
        # code stored inside basic blocks.
        for method_decl in node.method_decls:
            block_visitor = EmitBlocks()
            block_visitor.visit(method_decl.cfg)
            for instruction in block_visitor.code:
                node.cfg.append(instruction)

        # If -cfg flag is present in command line
        if self.viewcfg:
            for method_decl in node.method_decls:
                method_name = getattr(method_decl, "name", None)
                if method_name is not None:
                    method_name = method_name.name
                else:
                    method_name = "main"

                dot = CFG(f"@{node.name.name}.{method_name}")
                dot.view(method_decl.cfg)

    def visit_VarDecl(self, node: VarDecl):
        pass

    def visit_MethodDecl(self, node: MethodDecl):
        pass

    def visit_MainMethodDecl(self, node: MainMethodDecl):
        pass

    def visit_ParamList(self, node: ParamList):
        pass

    def visit_ParamDecl(self, node: ParamDecl):
        pass

    def visit_Compound(self, node: Compound):
        # Visit the block items
        for statement in node.statements:
            self.visit(statement)

    def visit_If(self, node: If):
        pass

    def visit_While(self, node: While):
        pass

    def visit_For(self, node: For):
        pass

    def visit_DeclList(self, node: DeclList):
        pass

    def visit_Print(self, node: Print):
        pass

    def visit_Assert(self, node: Assert):
        pass

    def visit_Break(self, node: Break):
        pass

    def visit_Return(self, node: Return):
        pass

    def visit_Assignment(self, node: Assignment):
        pass

    def visit_BinaryOp(self, node: BinaryOp):
        pass

    def visit_UnaryOp(self, node: UnaryOp):
        pass

    def visit_ArrayRef(self, node: ArrayRef):
        pass

    def visit_FieldAccess(self, node: FieldAccess):
        pass

    def visit_MethodCall(self, node: MethodCall):
        pass

    def visit_Length(self, node: Length):
        # Visit the expression to set its gen location
        self.visit(node.expr)
        # Alloc a register to store the length
        node.gen_loc = self.new_temp()
        # gen the length instruction
        length_inst = ("length", node.expr.gen_loc, node.gen_loc)
        # Store the length instruction
        self.current_block.append(length_inst)

    def visit_NewArray(self, node: NewArray):
        pass

    def visit_NewObject(self, node: NewObject):
        pass

    def visit_Constant(self, node: Constant):
        pass

    def visit_This(self, node: This):
        pass

    def visit_ID(self, node: ID):
        pass

    def visit_Type(self, node: Type):
        pass

    def visit_Extends(self, node: Extends):
        pass

    def visit_ExprList(self, node: ExprList):
        pass

    def visit_InitList(self, node: InitList):
        pass

    # TODO: Complete.


def main():
    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file",
        help="Path to file to be used to generate MJIR. By default, this script only runs the interpreter on the MJIR. \
              Use the other options for printing the MJIR, generating the CFG or for the debug mode.",
        type=str,
    )
    parser.add_argument(
        "--ir",
        help="Print MJIR generated from input_file.",
        action="store_true",
    )
    parser.add_argument(
        "--ir-pp",
        help="Print MJIR generated from input_file. (pretty print)",
        action="store_true",
    )
    parser.add_argument(
        "--cfg",
        help="Show the cfg of the input_file.",
        action="store_true",
    )

    args = parser.parse_args()

    print_ir = args.ir
    print_ir_pp = args.ir_pp
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

    gen = CodeGenerator(create_cfg)
    gen.visit(ast)
    gencode = gen.code

    if print_ir:
        print("Generated uCIR: --------")
        rich.print(gencode)
        print("------------------------\n")

    elif print_ir_pp:
        print("Generated uCIR: --------")
        gen.show()
        print("------------------------\n")

    else:
        vm = MJIRInterpreter()
        vm.run(gencode)


if __name__ == "__main__":
    main()
