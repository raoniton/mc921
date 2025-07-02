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
    StringArrayType,
    VoidType,
    MethodType,
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
    
    #""" check if an ID(variable name, parameter name, etc) has already been declared in the 
    #    current scope, instead of look up the whole program"""
    #def lookup_in_current_scope(self, name):
    #    return name in self.scopes[-1]


# stack of scopes to deal with blocks  '{} == metodos, classes, etc', we push diferent scopes inside the stack
class ScopedSymbolTable:
    
    def __init__(self, name=None, parent=None):
        self.name = name
        self.parent = parent
        self.scope_stack = parent.scope_stack.copy() if parent else []
        self.push_scope()

    
    def push_scope(self):
        #print("PUSHING scope")
        self.scope_stack.append(SymbolTable())

    def pop_scope(self):
        #print("POPING scope")
        self.scope_stack.pop()
    
    def add(self, name, value):
        #print(f"ADD: {name} -> {value}")
        self.scope_stack[-1].add(name, value)

    def lookup(self, name):
        #print(f"LOOKUP: {name}")
        # we are dealing with this as a stack, the last scope is at the end of the list,
        # to garantee the LIFO behavior we reversed
        for scope in reversed(self.scope_stack):
            resp = scope.lookup(name)
            if resp is not None:
                #print(f"  FOUND in scope: {name} -> {resp}")
                return resp
        #print(f"  NOT FOUND: {name}")
    
    def lookup_in_current_scope(self, name):
        return name in self.scope_stack[-1].data

# Store name, return type and param type from each method.
# Allow later check, e.g. methods call with right arguments
class MethodSymbol:
    def __init__(self, name, return_type):
        self.name = name
        self.return_type = return_type
        self.params = []  # list of param types

    def __repr__(self):
        return f"<MethodSymbol name={self.name}, return_type={self.return_type}, params={self.params}>"


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
        #self.global_symtab = SymbolTable()
        self.global_symtab = ScopedSymbolTable("global", parent=None)
        self.typemap = {
            "boolean": BooleanType,
            "char": CharType,
            "int": IntType,
            "String": StringType,
            "String[]": StringArrayType,
            "void": VoidType,
            "int[]": IntArrayType,
            "char[]": CharArrayType,
            "method": MethodType,
            "object": ObjectType,
        }
    
    def visit_Program(self, node: Program):
        #print("SB_Program::\n", node)
        """Visit the program node to fill in the global symbol table"""
        # First, register all classes in the program.
        # Populating the global symbol table with these classes
        for class_decl in node.class_decls:

            class_name = class_decl.name.name

            # Verifica duplicata aqui antes de adicionar
            assert_semantic(
                condition=(self.global_symtab.lookup(class_name) is None),
                error_type=SE.ALREADY_DECLARED_CLASS,
                coord=class_decl.coord,
                name=class_name,
            )


            class_symtab = ScopedSymbolTable(class_decl.name.name, self.global_symtab)
            self.global_symtab.add(class_decl.name.name, class_symtab)

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
            #super_class_name = node.extends.name
            superclass_decl = self.global_symtab.lookup(node.extends.name)
            
            #thow an semantic error 
            assert_semantic(
                condition=(superclass_decl is not None),
                error_type=SE.UNDECLARED_CLASS,
                coord=node.coord,
                name=node.extends.name,
            )

            # save the superclass for future searches ##
            self.current_class.superclass = superclass_decl

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
        #thow an semantic error
        assert_semantic(
            condition=(self.current_class.lookup(node.name.name) is None), 
            error_type=SE.ALREADY_DECLARED_FIELD,
            coord=node.coord,
            name=node.name.name,
        )

        # Now, record the field and its type
        # from SymbolTableBuilder we get the typemap, node.name.name == "int", then we save in var_type_field = IntType
        var_type_field = self.typemap.get(node.type.name)
        if var_type_field is None:
            var_type_field = self.global_symtab.lookup(node.type.name)
            assert_semantic(
                condition=(var_type_field is not None),
                error_type=SE.UNDECLARED_CLASS,
                coord=node.coord,
                name=node.type.name,
            )
            var_type = ObjectType(node.type.name)
        else:
            var_type = var_type_field # instancia o IntType(), Boolean()

        self.current_class.add(node.name.name, var_type) # record fole and its type

        

    def visit_MethodDecl(self, node: MethodDecl):
        # First, check if the method has already been declared
        assert_semantic(
            condition=(self.current_class.lookup(node.name.name) is None), 
            error_type=SE.ALREADY_DECLARED_METHOD,
            coord=node.coord,
            name=node.name.name,
        )

        return_type_class = self.typemap.get(node.type.name)         
        assert_semantic(
            condition=(return_type_class is not None), 
            error_type=SE.RETURN_TYPE_MISMATCH,
            coord=node.coord,
            name=node.type.name,
        )

        #instancia o tipo do retorno
        return_type = return_type_class

        # Gather parameter types
        #print(node)
        #print(type(node.param_list))

        param_list = node.param_list
        if isinstance(param_list, ParamList):
            param_list = param_list.params
        
        param_types = []
        param_names = []
        for param in param_list:
            param_type_method = self.typemap.get(param.type.name)
            
            assert_semantic(
                condition=(param_type_method is not None),
                error_type=SE.UNDECLARED_CLASS,
                coord=param.coord,
                name=param.type.name,
            )
            param_names.append(param.name.name)
            param_types.append(param_type_method)
        
        
        # Now, record the method and its signature
        method_type = MethodType(return_type, param_types)
        method_type.param_names = param_names
        self.current_class.add(node.name.name, method_type)

    def visit_MainMethodDecl(self, node: MainMethodDecl):
        # The main method must have the name "main"
        # First, check if the main method has already been declared
        assert_semantic(
            condition=(self.current_class.lookup("main") is None),
            error_type=SE.ALREADY_DECLARED_METHOD,
            coord=node.coord,
            name="main",
        )

        # Now, record the main method and its signature
        return_type = self.typemap["void"]
        param_types = [self.typemap["String"]]  # String[] args

        method_type = MethodType(return_type, param_types)
        self.current_class.add("main", method_type)


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
        self.scope = ScopedSymbolTable()
        self.typemap = {
            "boolean": BooleanType,
            "char": CharType,
            "int": IntType,
            "String": StringType,
            "String[]": StringArrayType,
            "void": VoidType,
            "int[]": IntArrayType,
            "char[]": CharArrayType,
            "method": MethodType,
            "object": ObjectType,
        }
        self.main_declared = False
        self.current_class_name = None
        self.current_method_return_type = None
        self.current_loop = None


    def _find_field_in_class_or_super(self, class_scope, field_name, coord):
        current_scope = class_scope
        while current_scope:
            found_type = current_scope.lookup(field_name)
            if found_type:
                return found_type
            current_scope = getattr(current_scope, 'superclass', None)

        # if didn't find, throw semantic error
        assert_semantic(
            condition=False,
            error_type=SE.UNDECLARED_FIELD,
            coord=coord,
            name=field_name,
        )

    # auxiliar method to check if the declared type is eq the actual
    def is_type_compatible(self, declared: MJType, actual: MJType) -> bool:
        if declared is None or actual is None:
            return False
        
        if declared is actual:
            return True
    
        if declared is CharArrayType and actual is StringType:
            return True
        
        # check if the objects have the same tipe and class name.
        if isinstance(actual, ObjectType) and isinstance(declared, ObjectType):
            if declared.typename == actual.typename:
                return True
            
            # check if actual.typename is declared.typename's subclass
            current_class = self.global_symtab.lookup(actual.typename)
            while current_class is not None:
                superclass = getattr(current_class, "superclass", None)
                if superclass is None:
                    break
                if superclass.name == declared.typename:
                    return True
                current_class = superclass


        return False


    def visit_Program(self, node: Program):
        #print("[DEBUG] SA_Program::\n",node)
        
        # check for duplicate of classes
        seen = set() # create an empty set to store classes already declared(has seen already)
        for cls in node.class_decls:
            if cls.name.name in seen:
                assert_semantic(
                    False,
                    SE.ALREADY_DECLARED_CLASS,
                    coord=cls.coord,
                    name=cls.name.name,
                )
            # even if we identify a duplicated cls, we add in the table, cuz it can contain another errors inside 
            # and will need to flag that
            seen.add(cls.name.name) 


        # visit all class declarations in the program
        for cls in node.class_decls:
            self.visit(cls)


    def visit_ClassDecl(self, node: ClassDecl):
        #print("[DEBUG] SA_ClassDecl::\n",node)
        self.current_class_name = node.name.name

        # Check if an specific class is on the symbol table
        class_scope = self.global_symtab.lookup(self.current_class_name)
        assert_semantic(
            condition=(class_scope is not None),
            error_type=SE.UNDECLARED_CLASS,
            coord=node.coord,
            name=self.current_class_name,
        )

        # If inheritance is present, check whether the superclass exists (redundant if already done during symbol table construction)
        if node.extends is not None:
            superclass_name = node.extends.name
            superclass_scope = self.global_symtab.lookup(superclass_name)
            assert_semantic(
                condition=(superclass_scope is not None),
                error_type=SE.UNDECLARED_CLASS,
                coord=node.coord,
                name=superclass_name,
            )

        # Visit fields
        for field in node.var_decls:
            self.visit(field)

        # Visit methods (declarations and bodies)
        for method in node.method_decls:
            self.visit(method)

        # Remove class context after finish
        self.current_class_name = None


    def visit_VarDecl(self, node: VarDecl):
        #print(f"[DEBUG] VarDecl {node.name.name} init type: {type(node.init)}")
        class_name = node.type.name.name if hasattr(node.type.name, 'name') else node.type.name
        declared_type_class = self.typemap.get(class_name) # Get the declared type "int", "char[]

        # If didn't find the type in the typemap, try find in global_symtab
        if declared_type_class is None:
            
            user_class = self.global_symtab.lookup(class_name)
            assert_semantic(
                condition=(user_class is not None),
                error_type=SE.UNDECLARED_CLASS,
                coord=node.coord,
                name=class_name,
            )
            declared_type_class = ObjectType(class_name)

        declared_type = declared_type_class 

        # check if variable is not already declared in current scope
        assert_semantic(
            condition=not self.scope.lookup_in_current_scope(node.name.name),
            error_type=SE.ALREADY_DECLARED_NAME,
            coord=node.coord,
            name=node.name.name,
        )

        # check if it has an init int x = 5
        if isinstance(node.init, Node):
            expr_type = self.visit(node.init)   # Visit the initializer expression to get its type
            
            # Check if the compatility between declared type and initializer's type
            assert_semantic(
                condition=self.is_type_compatible(declared_type, expr_type),
                error_type=SE.ASSIGN_TYPE_MISMATCH,
                coord=node.coord,
                ltype=str(declared_type),
                rtype=str(expr_type),
            )

        # Register the variable in the current scope with its declared type
        self.scope.add(node.name.name, declared_type)


    def visit_MethodDecl(self, node: MethodDecl):
        #print("SA_MethodDecl::\n",node)
        method_name = node.name.name

        # Recover information from actual class and method
        class_scope = self.global_symtab.lookup(self.current_class_name)
        assert_semantic(
            condition=(class_scope is not None),
            error_type=SE.UNDECLARED_CLASS,
            coord=node.coord,
            name=self.current_class_name,
        )

        method_info = class_scope.lookup(method_name)
        assert_semantic(
            condition=(method_info is not None),
            error_type=SE.UNDECLARED_METHOD,
            coord=node.coord,
            name=method_name,
        )

        # Define the actual return type for validation 'return'
        self.current_method_return_type = method_info.return_type

        # Get inside method scope
        self.scope.push_scope()

        param_list = node.param_list
        if isinstance(param_list, ParamList):
            param_list = param_list.params
        
        # Add the params to the scope
        for param, param_type in zip(param_list, method_info.param_types):
            assert_semantic(
                condition=not self.scope.lookup_in_current_scope(param.name.name),
                error_type=SE.PARAMETER_ALREADY_DECLARED,
                coord=param.coord,
                name=param.name.name,
            )
            self.scope.add(param.name.name, param_type)

        # Visit body's method
        self.visit(node.body)

        # Get out from method scope
        self.scope.pop_scope()
        self.current_method_return_type = None


    def visit_MainMethodDecl(self, node: MainMethodDecl):
        #print("[DEBUB] SA_MainMethodDecl::\n",node)
        # Impede múltiplas declarações de main
        assert_semantic(
            not self.main_declared,
            error_type=SE.ALREADY_DECLARED_METHOD,
            coord=node.coord,
            name="main",
        )
        self.main_declared = True

        # Get actual class
        class_scope = self.global_symtab.lookup(self.current_class_name)
        assert_semantic(
            condition=(class_scope is not None),
            error_type=SE.UNDECLARED_CLASS,
            coord=node.coord,
            name=self.current_class_name,
        )

        # Get the main method definition
        method_info = class_scope.lookup("main")
        assert_semantic(
            condition=(method_info is not None),
            error_type=SE.UNDECLARED_METHOD,
            coord=node.coord,
            name="main",
        )

        # Define the expected return type
        self.current_method_return_type = method_info.return_type

        # Get in main method scope
        self.scope.push_scope()

        # Add args params (String[] args)
        assert_semantic(
            condition=len(method_info.param_types) == 1,
            error_type=SE.ARGUMENT_COUNT_MISMATCH,
            coord=node.coord,
            name="main",
        )
        param_type = method_info.param_types[0]

        self.scope.add(node.args.name, param_type)

        # Visit main method body
        self.visit(node.body)

        # Get out main method scope
        self.scope.pop_scope()
        self.current_method_return_type = None


    def visit_ParamList(self, node: ParamList):
        for param in node.params:
            self.visit(param)


    def visit_ParamDecl(self, node: ParamDecl):
        param_type_class = self.typemap.get(node.type.name)
        assert_semantic(
            condition=(param_type_class is not None),
            error_type=SE.UNDECLARED_CLASS,
            coord=node.coord,
            name=node.type.name,
        )
        param_type = param_type_class()

        # check if the parameter has already been declared
        if self.scope.lookup_in_current_scope(node.name.name):
            assert_semantic(
                False,
                SE.PARAMETER_ALREADY_DECLARED,
                coord=node.coord,
                name=node.name.name,
            )

        # Add the param in the current scope
        self.scope.add(node.name.name, param_type)

        
    def visit_Compound(self, node: Compound):
        self.scope.push_scope()

        for stmt in node.statements:
            self.visit(stmt)

        self.scope.pop_scope()


    def visit_If(self, node: If):
        #print(f"[DEBUG] visit_If: condition = {node.cond}")
        #print(f"[DEBUG] condition type = {type(node.cond)}")

        condition_type = self.visit(node.cond) # we get the return to check if it is boolean type
        assert_semantic(
            condition=(condition_type == self.typemap["boolean"]),
            error_type=SE.CONDITIONAL_EXPRESSION_TYPE_MISMATCH,
            coord=node.coord,
            ltype=str(condition_type) #!= bool
        )

        #iftrue
        self.scope.push_scope()
        self.visit(node.iftrue)
        self.scope.pop_scope()

        #ifflase
        if node.iffalse is not None:
            self.scope.push_scope()
            self.visit(node.iffalse)
            self.scope.pop_scope()
        

    def visit_While(self, node: While):
        # we save references to current and next iteration
        current_ref = self.current_loop
        self.current_loop = node

        condition_type = self.visit(node.cond)
        assert_semantic(
            condition=(condition_type == self.typemap["boolean"]),
            error_type=SE.CONDITIONAL_EXPRESSION_TYPE_MISMATCH,
            coord=node.coord,
            ltype=str(condition_type) #!= bool
        )

        self.scope.push_scope()
        self.visit(node.body)
        self.scope.pop_scope()

        """ 
        here we recover the previous reference, lets say that we have a for/while nested in another for/while 
        if we use a "break" or a "continue" at the inside for/while, the outside for/while has to continue doing his job 
        that's is the reason for "self.current_loop = current_ref
        """
        self.current_loop = current_ref


    def visit_For(self, node: For):
        # we save references to current and next iteration
        current_ref = self.current_loop
        self.current_loop = node

        self.scope.push_scope()

        #     init     cond     next
        #      |         |       |
        # for(int i=0; i < 10; i++)

        # initialization
        if node.init is not None:
            self.visit(node.init)
        
        # condition
        if node.cond is not None:
            condition_type = self.visit(node.cond)
            assert_semantic(
                condition=(condition_type == self.typemap["boolean"]),
                error_type=SE.CONDITIONAL_EXPRESSION_TYPE_MISMATCH,
                coord=node.coord,
                ltype=str(condition_type) #!= bool
            )
        
        # increment - next
        if node.next is not None:
            self.visit(node.next)
        
        
        # visit the for's body
        self.visit(node.body)
        
        self.scope.pop_scope()

        """ 
        here we recover the previous reference, lets say that we have a for/while nested in another for/while 
        if we use a "break" or a "continue" at the inside for/while, the outside for/while has to continue doing his job 
        that's is the reason for "self.current_loop = current_ref
        """
        self.current_loop = current_ref
    

    def visit_DeclList(self, node: DeclList):
        for decl in node.decls:
            self.visit(decl)


    def visit_Print(self, node: Print):
        #print("[DEBUG] SA_PRINT::\n",node)
        #print("Print node.expr:", node.expr)

        # if print(), in other words, if it has no arguments
        if node.expr is None:
            return
        
        allowed_types = [CharType, IntType, StringType]
        if isinstance(node.expr, ExprList): #sometimes we deal with a ExprList and sometimes not a list
            exprs = node.expr.exprs
        else:
            exprs = [node.expr] # if is just a expr, we put it into a list

        for expr in exprs:
            #print(type(expr))
            expr_type = self.visit(expr)
            assert_semantic(
                condition=(expr_type in allowed_types),
                error_type=SE.PRINT_EXPRESSION_TYPE_MISMATCH,
                coord=node.coord,
            )


    def visit_Assert(self, node: Assert):
        expr_type = self.visit(node.expr)
        assert_semantic(
            condition=(expr_type == self.typemap["boolean"]),
            error_type=(SE.ASSERT_EXPRESSION_TYPE_MISMATCH),
            coord=node.coord,
        )


    def visit_Break(self, node: Break):
        assert_semantic(
            condition=(self.current_loop is not None),
            error_type=SE.WRONG_BREAK_STATEMENT,
            coord=node.coord
        )


    def visit_Return(self, node: Return):
        if node.expr is not None:
            return_expr_type = self.visit(node.expr)
        else:
            return_expr_type = VoidType

        assert_semantic(
            condition=return_expr_type == self.current_method_return_type,
            error_type=SE.RETURN_TYPE_MISMATCH,
            coord=node.coord,
            ltype=str(return_expr_type),
            rtype=str(self.current_method_return_type),
        )

        return return_expr_type


    def visit_Assignment(self, node: Assignment):
        #print(f"[DEBUG] Assignment {node.lvalue} = {node.rvalue}")

        rvalue_type = self.visit(node.rvalue)
        lvalue_type = self.visit(node.lvalue)

        assert_semantic(
            self.is_type_compatible(lvalue_type, rvalue_type),
            SE.ASSIGN_TYPE_MISMATCH,
            coord=node.coord,
            ltype=str(lvalue_type),
            rtype=str(rvalue_type),
        )

        return lvalue_type


    def visit_BinaryOp(self, node: BinaryOp):
        #print(f"[DEBUG] visit_BinaryOp: {node.op} @ {node.coord}")
        
        rtype = self.visit(node.rvalue)
        ltype = self.visit(node.lvalue)
        
        # Check if left and right operands have the same type
        assert_semantic(
            condition=self.is_type_compatible(ltype, rtype),
            error_type=SE.BINARY_EXPRESSION_TYPE_MISMATCH,
            coord=node.coord,
            name=node.op,
        )
  
        # Check if the operation is supported by the type 
        # Assign the type of the result of the binary expression
        if node.op in ltype.binary_ops:
            return ltype  # ops like +, -, *, etc

        elif node.op in ltype.rel_ops:
            return BooleanType  # op like ==, <, >=, etc

        elif node.op in {"&&", "||"}:
            assert_semantic(
                condition=(ltype == BooleanType),
                error_type=SE.UNSUPPORTED_BINARY_OPERATION,
                coord=node.coord,
                name=node.op,
                ltype=str(ltype),
            )
            return BooleanType
    
        # unsupported operator
        assert_semantic(
            condition=False,
            error_type=SE.UNSUPPORTED_BINARY_OPERATION,
            coord=node.coord,
            name=node.op,
            ltype=str(ltype),
        )
        

    def visit_UnaryOp(self, node: UnaryOp):
        expr_type = self.visit(node.expr)
        #print(f"[DEBUG UnaryOP] UnaryOp: op={node.op}, expr_type={expr_type}")

        if node.op == '!':
            assert_semantic(
                expr_type == BooleanType,
                error_type=SE.UNSUPPORTED_UNARY_OPERATION,
                coord=node.coord,
                name=node.op,
            )
            return BooleanType

        elif node.op in {'-', '+'}:
            assert_semantic(
                expr_type == IntType,
                error_type=SE.UNSUPPORTED_UNARY_OPERATION,
                coord=node.coord,
                name=node.op,
            )
            return IntType

        # Operador desconhecido
        assert_semantic(
            condition=False,
            error_type=SE.UNSUPPORTED_UNARY_OPERATION,
            coord=node.coord,
            name=node.op,
        )


    def visit_ArrayRef(self, node: ArrayRef):
        
        subscript_type = self.visit(node.subscript)
        assert_semantic(
            condition=(subscript_type is IntType),
            error_type=SE.ARRAY_DIMENTION_MISMATCH,
            coord=node.coord,
            ltype=str(subscript_type),
        )

        array_type = self.visit(node.name)
        #print(f"[DEBUG] visit_ArrayRef: subscript_type = {subscript_type}")
        #print(f"[DEBUG] visit_ArrayRef: array_type = {array_type} ({type(array_type)})")

        
        assert_semantic(
            condition=(array_type is IntArrayType or array_type is CharArrayType),
            error_type=SE.ARRAY_REF_TYPE_MISMATCH,
            coord=node.coord,
            ltype=str(array_type),
        )

        if array_type is IntArrayType:
            return IntType
        else:  # CharArrayType
            return CharType


    def visit_FieldAccess(self, node: FieldAccess):
        #print("[DEBUG] SA_FieldAccess: "node)
        # ex: a.b -- object 'a' that has a field called 'b'
        obj_type = self.visit(node.object)
        
        assert_semantic(
            condition=(obj_type is not None),
            error_type=SE.UNDECLARED_NAME,
            coord=node.coord,
            name=node.object,
        )

        # check if obj_type is not a primitive type
        assert_semantic(
            condition=isinstance(obj_type, ObjectType),
            error_type=SE.OBJECT_TYPE_MUST_BE_A_CLASS,
            coord=node.coord,
            name=getattr(node.object, "name", "this"),
        )

        # recover the class context to verify class' fields
        class_symbol = self.global_symtab.lookup(obj_type.typename)
        assert_semantic(
            condition=(class_symbol is not None),
            error_type=SE.UNDECLARED_FIELD,
            coord=node.coord,
            name=obj_type.typename,
        )

        
        # Check that the requested field exists in the object’s class or its parent classes.
        field_type = self._find_field_in_class_or_super(class_symbol, node.field_name.name, node.coord)
        #_find_field_in_class_or_super lanca o assert_semantic - UNDECLARED_FIELD
        
        node.type = field_type
        return field_type


    def visit_MethodCall(self, node: MethodCall):
        #print(f"Tipo do nó init da var 'obj': {type(node.init)}")
        #print(f"Conteúdo do init: {node.init}")
        obj_type = self.visit(node.object) #we visit the object on which the method will be called
        assert_semantic(
            condition=obj_type is not None,
            error_type=SE.UNDECLARED_NAME,
            coord=node.object.coord,
            name=node.object,
        )

        # Verifica se o tipo do objeto é uma classe
        assert_semantic(
            condition=isinstance(obj_type, ObjectType),
            error_type=SE.OBJECT_TYPE_MUST_BE_A_CLASS,
            coord=node.object.coord,
            name=node.object,
        )

        # get the class definition from global_scope
        class_info = self.global_symtab.lookup(obj_type.typename)
        assert_semantic(
            condition=class_info is not None,
            error_type=SE.UNDECLARED_CLASS,
            coord=node.object.coord,
            name=obj_type.typename,
        )

        # Check if the method exists in the object’s class
        method_name = node.method_name.name
        method_info = class_info.lookup(method_name)


        assert_semantic(
            condition=method_info is not None,
            error_type=SE.UNDECLARED_METHOD,
            coord=node.coord,
            name=method_name,
        )
        
        # not all times is a ExprList, sometimes it's an ID, so we do a IF, to cover those possiblities
        if isinstance(node.args, ExprList):
            args = node.args.exprs
        elif node.args is not None:
            args = [node.args]
        else:
            args = []

        param_types = method_info.param_types
        param_names = method_info.param_names    

        # if the number of arguments are different than numer of param, throw semantic error
        assert_semantic(
            condition=len(args) == len(param_types),
            error_type=SE.ARGUMENT_COUNT_MISMATCH,
            coord=node.coord,
            name=method_name,
        )

        # Verifica se tipos dos argumentos batem com os tipos dos parâmetros
        for i, (arg, expected_type, param_name) in enumerate(zip(args, param_types, param_names)):
            arg_type = self.visit(arg)
            #print(f"[DEBUG]-SA_METHODCALL Arg {i}: name={param_name}, coord={arg.coord}, type={arg_type}, expected={expected_type}")
            assert_semantic(
                condition=arg_type == expected_type,
                error_type=SE.PARAMETER_TYPE_MISMATCH,
                coord=node.coord,
                name=param_name,
            )
        # Define o tipo do nó como o tipo de retorno do método
        node.type = method_info.return_type
        return node.type


    def visit_Length(self, node: Length):
        expr_type = self.visit(node.expr)

        # check if is an ArrayType of StringType (array ou string)
        is_valid = expr_type in (IntArrayType, CharArrayType, StringType)
        assert_semantic(
            condition=is_valid,
            error_type=SE.INVALID_LENGTH_TARGET,
            coord=node.coord,
            name=str(expr_type)
        )

        # .length returns an int
        node.type = IntType
        return node.type


    def visit_NewArray(self, node: NewArray):
        size_type = self.visit(node.size)
        #print("[DEBUG] SA_NewArray::\n", node)
        #print("[DEBUG] SA_NewArray::\n", type(size_type))
        
        assert_semantic(
            condition=(size_type == IntType),
            error_type=SE.ARRAY_DIMENTION_MISMATCH,
            coord=node.coord,
        )

        # Define o tipo do array com base no tipo do elemento
        base_type = self.visit(node.type)
        #print(base_type)

        if base_type == IntArrayType:
            node.mj_type = IntArrayType
        elif base_type == CharArrayType:
            node.mj_type = CharArrayType
        else:
            assert_semantic(
                False,
                error_type=SE.UNDECLARED_CLASS,
                coord=node.coord,
                name=base_type.typename,
            )

        return node.mj_type


    def visit_NewObject(self, node: NewObject):
        #print("[DEBUG] SA_NewObject::\n", node)
        class_name = node.type.name.name
        class_info = self.global_symtab.lookup(class_name)
        
        assert_semantic(
            condition=class_info is not None,
            error_type=SE.UNDECLARED_CLASS,
            coord=node.coord,
            name=class_name,
        )

        node.type = ObjectType(class_name)
        return node.type


    def visit_Constant(self, node: Constant):
        value = node.value
        #print("[DEBUG]-SA_Constant::", node, "  visit_Constant:", node.value, "type:", node.type)
                
        if isinstance(value, bool):
            node.type = BooleanType
        elif isinstance(value, int):
            node.type = IntType
        elif isinstance(value, str):
            if node.type == 'char':
                node.type = CharType
            else:
                node.type = StringType
        else:
            node.type = None

        return node.type


    def visit_This(self, node: This):
        # Check if we are currently inside a class context(in visit_ClassDecl)
        # Define o tipo do nó como o tipo do objeto da classe atual
        node.type = ObjectType(self.current_class_name)
        return node.type
    

    def visit_ID(self, node: ID):
        #print(f"[DEBUG-ID] Looking up {node.name}")
        symbol = self.scope.lookup(node.name)

        assert_semantic(
            condition=symbol is not None,
            error_type=SE.UNDECLARED_NAME,
            coord=node.coord,
            name=node.name,
        )

        node.type = symbol
        return node.type


    def visit_Type(self, node: Type):
        node.type = self.typemap.get(node.name)
        return node.type


    def visit_Extends(self, node: Extends):
        #print("DEBUG-SA_Extends", node)
        superclass_name = node.superclass.name
        superclass_symbol = self.global_scope.lookup(superclass_name)

        assert_semantic(
            condition=superclass_symbol is not None,
            error_type=SE.UNDECLARED_CLASS,
            coord=node.coord,
            name=superclass_name,
        )


    def visit_ExprList(self, node: ExprList):
        for expr in node.exprs:
            self.visit(expr)


    def visit_InitList(self, node: InitList):
        #print("[DEBUG-SA_InitList] visit_InitList:", node)
        
        element_types = []
        element_values = []
        for expr in node.exprs:
            # check if theh value is a Constant
            assert_semantic(
                condition=isinstance(expr, Constant),
                error_type=SE.NOT_A_CONSTANT,
                coord=expr.coord
            )

            expr_type=self.visit(expr)
            element_types.append(expr_type)
            element_values.append(expr.value)
        

        if not element_types:
            # Empty list: don't define type or define generic type, depend on the needs
            node.type = None
            return

        
        # Check if all elements have the same type
        first_type = element_types[0]
        for i, t in enumerate(element_types):
            
            assert_semantic(
                condition=(t is first_type),
                error_type=SE.ARRAY_ELEMENT_TYPE_MISMATCH,
                coord=node.exprs[i].coord,
                ltype=first_type,
                rtype=t,
                name=element_values[i],
            )
       
        # Define InitList type as the type of all elements from this array
        if first_type is IntType:
            node.type = IntArrayType
        elif first_type is CharType:
            node.type = CharArrayType
        else:
            assert_semantic(
                False,
                error_type=SE.ARRAY_ELEMENT_TYPE_MISMATCH,
                coord=node.coord,
                name=str(first_type),
            )
        
        return node.type

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
