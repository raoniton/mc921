import argparse
import pathlib
import sys
from copy import deepcopy
from typing import Any, Dict, Union

from mjc.mj_ast import *
from mjc.mj_parser import MJParser
from mjc.mj_serror import SE, assert_semantic
from mjc.mj_type import (
    BooleanType,
    CharArrayType,
    CharType,
    IntArrayType,
    IntType,
    MJType,
    ObjectType,
    StringType,
    VoidType,
)


class SymbolTable:
    """Class representing a symbol table.

    `add` and `lookup` methods are given, however you still need to find a way to
    deal with scopes.

    ## Attributes
    :data: the content of the SymbolTable
    """

    def __init__(self) -> None:
        """Initializes the SymbolTable."""
        self.__data = dict()

    @property
    def data(self) -> Dict[str, Any]:
        """Returns a copy of the SymbolTable."""
        return deepcopy(self.__data)

    def add(self, name: str, value: Any) -> None:
        """Adds to the SymbolTable.

        :param name: the identifier on the SymbolTable
        :param value: the value to assign to the given `name`
        """
        self.__data[name] = value

    def lookup(self, name: str) -> Union[Any, None]:
        """Searches `name` on the SymbolTable and returns the value
        assigned to it.

        :param name: the identifier that will be searched on the SymbolTable
        :return: the value assigned to `name` on the SymbolTable. If `name` is not found, `None` is returned.
        """
        return self.__data.get(name)


class NodeVisitor:
    """A base NodeVisitor class for visiting uc_ast nodes.
    Subclass it and define your own visit_XXX methods, where
    XXX is the class name you want to visit with these
    methods.
    """

    _method_cache = None

    def visit(self, node):
        """Visit a node."""

        if self._method_cache is None:
            self._method_cache = {}

        visitor = self._method_cache.get(node.__class__.__name__)
        if visitor is None:
            method = "visit_" + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            self._method_cache[node.__class__.__name__] = visitor

        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a
        node. Implements preorder visiting of the node.
        """
        for _, child in node.children():
            self.visit(child)


class SymbolTableBuilder(NodeVisitor):
    """Symbol Table Builder class.
    This class build the Symbol table of the program by visiting all the AST nodes
    using the visitor pattern.
    """

    def __init__(self):
        self.global_symtab = SymbolTable()
        self.typemap = {
            "boolean": BooleanType,
            "char": CharType,
            "int": IntType,
            "String": StringType,
            "void": VoidType,
            "int[]": IntArrayType,
            "char[]": CharArrayType,
            "object": ObjectType,
        }

    def visit_Program(self, node: Program):
        """Visit the program node to fill in the global symbol table"""
        # First, register all classes in the program.
        # Populating the global symbol table with these classes
        for class_decl in node.class_decls:
            pass

        # Now, process each class to fill in fields and methods
        for class_decl in node.class_decls:
            self.visit(class_decl)

        # Finally, return the global symtab to use in the next steps
        return self.global_symtab

    def visit_ClassDecl(self, node: ClassDecl):
        # Set the current class to ensure the context for internal visits
        self.current_class = self.global_symtab.lookup(node.name.name)

        # First, if the class extends another, check that the parent exists.
        if node.extends is not None:
            pass

        # Then, visit all fields (var_decls) of the class
        for field in node.var_decls:
            self.visit(field)

        # Finally, visit all class methods (method_decls)
        for method in node.method_decls:
            self.visit(method)

        # Unset the current class context
        self.current_class = None

    def visit_VarDecl(self, node: VarDecl):
        # First, check if the field has already been declared
        # Now, record the field and its type
        pass

    def visit_MethodDecl(self, node: MethodDecl):
        # First, check if the method has already been declared
        # Gather parameter types
        # Now, record the method and its signature
        pass

    def visit_MainMethodDecl(self, node: MainMethodDecl):
        # The main method must have the name "main"
        # First, check if the main method has already been declared
        # Now, record the main method and its signature
        pass


class SemanticAnalyzer(NodeVisitor):
    """Semantic Analyzer class.
    This class performs semantic analysis on the AST of a MiniJava program.
    You need to define methods of the form visit_NodeName()
    for each kind of AST node that you want to process.
    """

    def __init__(self, global_symtab: SymbolTable):
        """
        :param global_symtab: Global symbol table with all class declaration metadata.
        """
        self.global_symtab = global_symtab
        self.typemap = {
            "boolean": BooleanType,
            "char": CharType,
            "int": IntType,
            "String": StringType,
            "void": VoidType,
            "int[]": IntArrayType,
            "char[]": CharArrayType,
            "object": ObjectType,
        }

    def visit_Program(self, node: Program):
        # Visit all class declarations in the program
        for cls in node.class_decls:
            self.visit(cls)

    def visit_ClassDecl(self, node: ClassDecl):
        # Visit the fields of the class (var_decls)
        for field in node.var_decls:
            self.visit(field)

        # Then, visit the methods of the class (method_decls)
        for method in node.method_decls:
            self.visit(method)

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
        pass

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
        # Visit the right side
        self.visit(node.rvalue)

        # Visit the left side
        self.visit(node.lvalue)

        # Check if the name is defined
        if isinstance(node.lvalue, ID):
            assert_semantic(
                condition=(node.lvalue.scope is not None),
                error_type=SE.UNDECLARED_NAME,
                coord=node.coord,
                name=node.lvalue.name,
            )

        # Check if the assignment is allowed
        # TODO: Complete

    def visit_BinaryOp(self, node: BinaryOp):
        # Visit the left expression
        self.visit(node.lvalue)
        # Visit the right expression
        self.visit(node.rvalue)
        # Check if left and right operands have the same type
        ltype = node.lvalue.mj_type
        rtype = node.rvalue.mj_type
        assert_semantic(
            condition=(ltype == rtype),
            error_type=SE.BINARY_EXPRESSION_TYPE_MISMATCH,
            coord=node.coord,
            name=node.op,
            ltype=ltype,
            rtype=rtype,
        )
        # Check if the operation is supported by the type
        # Assign the type of the result of the binary expression
        # TODO: Complete

    def visit_UnaryOp(self, node: UnaryOp):
        pass

    def visit_ArrayRef(self, node: ArrayRef):
        pass

    def visit_FieldAccess(self, node: FieldAccess):
        pass

    def visit_MethodCall(self, node: MethodCall):
        pass

    def visit_Length(self, node: Length):
        pass

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


def main():
    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file", help="Path to file to be semantically checked", type=str
    )
    args = parser.parse_args()

    # get input path
    input_file = args.input_file
    input_path = pathlib.Path(input_file)

    # check if file exists
    if not input_path.exists():
        print("Input", input_path, "not found", file=sys.stderr)
        sys.exit(1)

    p = MJParser()
    # open file and parse it
    with open(input_path) as f:
        # Parse the code to an AST
        ast = p.parse(f.read())

        # First, build the global symtab
        global_symtab_builder = SymbolTableBuilder()
        global_symtab = global_symtab_builder.visit(ast)

        # Then, execute the semantic analysis
        sema = SemanticAnalyzer(global_symtab=global_symtab)
        sema.visit(ast)


if __name__ == "__main__":
    main()
