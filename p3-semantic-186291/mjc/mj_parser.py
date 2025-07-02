import argparse
import pathlib
import sys
from io import StringIO

from sly import Parser

from mjc.mj_ast import *
from mjc.mj_lexer import MJLexer


class Coord:
    """Coordinates of a syntactic element. Consists of:
    - Line number
    - (optional) column number, for the Lexer
    """

    __slots__ = ("line", "column")

    def __init__(self, line, column=None):
        self.line = line
        self.column = column

    def __str__(self):
        if self.line and self.column is not None:
            coord_str = "@ %s:%s" % (self.line, self.column)
        elif self.line:
            coord_str = "@ %s" % (self.line)
        else:
            coord_str = ""
        return coord_str


class ParserLogger:
    """Logger Class used to log messages about the parser in a text stream.
    NOTE: This class overrides the default SlyLogger class
    """

    def __init__(self):
        self.stream = StringIO()

    @property
    def text(self):
        return self.stream.getvalue()

    def debug(self, msg, *args, **kwargs):
        self.stream.write((msg % args) + "\n")

    info = debug

    def warning(self, msg, *args, **kwargs):
        self.stream.write("WARNING: " + (msg % args) + "\n")

    def error(self, msg, *args, **kwargs):
        self.stream.write("ERROR: " + (msg % args) + "\n")

    critical = debug


class MJParser(Parser):
    tokens = MJLexer.tokens
    start = "program"
    debugfile = "parser.debug"
    log = ParserLogger()

    def __init__(self, debug=True):
        """Create a new MJParser."""
        self.debug = debug
        self.mjlex = MJLexer(self._lexer_error)

        # Keeps track of the last token given to yacc (the lookahead token)
        self._last_yielded_token = None

    def parse(self, text):
        self._last_yielded_token = None
        return super().parse(self.mjlex.tokenize(text))

    def _lexer_error(self, msg, line, column):
        # use stdout to match with the output in the .out test files
        print("LexerError: %s at %d:%d" % (msg, line, column), file=sys.stdout)
        sys.exit(1)

    def _parser_error(self, msg, coord=None):
        # use stdout to match with the output in the .out test files
        if coord is None:
            print("ParserError: %s" % (msg), file=sys.stdout)
        else:
            print("ParserError: %s %s" % (msg, coord), file=sys.stdout)
        sys.exit(1)

    def _token_coord(self, p):
        last_cr = self.mjlex.text.rfind("\n", 0, p.index)
        if last_cr < 0:
            last_cr = -1
        column = p.index - (last_cr)
        return Coord(p.lineno, column)

    precedence = (
        ('right', 'ASSIGN'),
        ('left', 'OR'),
        ('left', 'AND'),
        ('left', 'EQ', 'NE'),
        ('left', 'LT', 'LE', 'GT', 'GE'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD'),
        ('right', 'NOT'),
        #('nonassoc', 'ELSE'),

    )

    # ------------------------------------------------------------
    # Parser Rules
    # ------------------------------------------------------------
    # <program> ::= {<class_declaration>}+
    @_("class_declaration_list")
    def program(self, p):
        #print("DEBUG: classes =", p.class_declaration_list)
        return Program(p.class_declaration_list)
    
    
    @_("class_declaration_list class_declaration")
    def class_declaration_list(self, p):
        return p.class_declaration_list + [p.class_declaration]
    
    @_("class_declaration")
    def class_declaration_list(self, p):
        return [p.class_declaration]

    # ------------------------------------------------------------
    # <class_declaration> ::= "class" <identifier> {<extends_expression>}? "{" {<compound_declaration>}* {<method_declaration>}* "}"

    @_("CLASS identifier extends_opt LBRACE compound_declaration_kstar  method_declaration_list RBRACE")
    def class_declaration(self, p):
        extends_node = None
        if p.extends_opt:
            extends_node = ID(p.extends_opt.super, p.extends_opt.coord)

        # Corrigindo: aplainar DeclLists em uma lista direta de VarDecls
        flat_var_decls = []
        for decl_list in p.compound_declaration_kstar:
            flat_var_decls.extend(decl_list.decls)

        return ClassDecl(
            name=p.identifier,
            extends=extends_node,
            var_decls=flat_var_decls,
            method_decls=p.method_declaration_list,
            coord=self._token_coord(p._slice[0])
        )
    
    
    #extends ? - opcional
    @_("extends_expression")
    def extends_opt(self, p):
        return p.extends_expression
        
    @_("empty")
    def extends_opt(self, p):
        return None
    

    #compound_declaration * - 0 ou mais
    """@_("compound_declaration_list compound_declaration")
    def compound_declaration_list(self, p):
        return  p.compound_declaration_list + [p.compound_declaration]
    
    @_("compound_declaration")
    def compound_declaration_list(self, p):
        return [p.compound_declaration]"""

    #method_declaration * - 0 ou mais
    @_("method_declaration_list method_declaration")
    def method_declaration_list(self, p):
        return p.method_declaration_list + [p.method_declaration]
    
    """@_("method_declaration")
    def method_declaration_list(self, p):
        return [p.method_declaration]"""
    
    @_("empty")
    def method_declaration_list(self, p):
        return []
    

    # ------------------------------------------------------------
    # EMPTY
    @_("")
    def empty(self, p):
        pass

    # ------------------------------------------------------------
    # <extends_expression> ::= "extends" <id>
    @_("EXTENDS ID")
    def extends_expression(self, p):
        return Extends(
            p.ID, self._token_coord(p._slice[0])
        )


    # ------------------------------------------------------------
    #<method_declaration> ::= <regular_method_declaration>
    #                  | <main_method_declaration>    
    @_("regular_method_declaration")
    def method_declaration(self, p):
        return p.regular_method_declaration

    @_("main_method_declaration")
    def method_declaration(self, p):
        return p.main_method_declaration

    # ------------------------------------------------------------
    # <regular_method_declaration> ::= "public" <type_specifier> <identifier> "(" <parameter_list>? ")" <compound_statement>
    @_("PUBLIC type_specifier identifier LPAREN parameter_list_opt RPAREN compound_statement")
    def regular_method_declaration(self, p):
        #print(f"DEBUG: regular_method_declaration -> name: {p.identifier.name}, body: {p.compound_statement}")
        return MethodDecl(
            type= p.type_specifier,
            name = p.identifier,
            param_list = p.parameter_list_opt,
            body = p.compound_statement,
            coord = self._token_coord(p._slice[0])
            
        )

    @_("parameter_list")
    def parameter_list_opt(self, p):
        return p.parameter_list

    @_("empty")
    def parameter_list_opt(self, p):
        return []
        
    # ------------------------------------------------------------
    # <main_method_declaration> ::= "public" "static" "void" "main" "(" "String" "[" "]" <identifier> ")" <compound_statement>
    @_("PUBLIC STATIC VOID MAIN LPAREN STRING LBRACK RBRACK ID RPAREN compound_statement")
    def main_method_declaration(self, p):
        #print("MATCHED MAIN") 
        #print(p.compound_statement)
        return MainMethodDecl(
            args=ID(p.ID, self._token_coord(p._slice[8])),
            body=p.compound_statement, 
            coord= self._token_coord(p._slice[0])
        )

    

    # ------------------------------------------------------------
    # <compound_declaration> ::= <type_specifier> <init_declarator_list> ";"
    @_('type_specifier init_declarator_list SEMICOLON')
    def compound_declaration(self, p):
        return DeclList(
            decls=[
                VarDecl(type=p.type_specifier, name=vd.name, init=vd.init, coord=vd.name.coord)
                for vd in p.init_declarator_list
            ], 
            coord=self._token_coord(p._slice[0])
    )

        
    
    # ------------------------------------------------------------
    #<init_declarator_list> ::= <init_declarator>
    #                     | <init_declarator_list> "," <init_declarator>

    # Lista com vários declaradores (ex: int x, y = 2;)
    @_("init_declarator_list COMMA init_declarator")
    def init_declarator_list(self, p):
        return p.init_declarator_list + [p.init_declarator] 

    @_("init_declarator")
    def init_declarator_list(self, p):
        return [p.init_declarator]

    # ------------------------------------------------------------
    #<init_declarator> ::= <declarator>
    #                | <declarator> "=" <initializer>

    # x = 5
    @_('declarator ASSIGN initializer')
    def init_declarator(self, p):
        return VarDecl(
            type=None,
            name=p.declarator,
            init=p.initializer,
            coord=self._token_coord(p._slice[0])
        )

    @_('declarator')
    def init_declarator(self, p):
        return VarDecl(
            type=None,  # será preenchido depois
            name=p.declarator,
            init=None,
            #coord=p.declarator.coord(p._slice[0])
            coord=self._token_coord(p._slice[0])
        )
    

    # ------------------------------------------------------------
    #<initializer> ::= <assignment_expression>
    #            | "{" {<initializer_list>}? "}"
    #            | "{" <initializer_list> "," "}"
    @_('assignment_expression')
    def initializer(self, p):
        return p.assignment_expression
    
    @_("LBRACE initializer_list_opt RBRACE")
    def initializer(self, p):
        return InitList(exprs=p.initializer_list_opt, coord=self._token_coord(p._slice[1]))

    @_("LBRACE initializer_list COMMA RBRACE")
    def initializer(self, p):
        return InitList(exprs=p.initializer_list, coord=self._token_coord(p._slice[1]))

    @_("initializer_list")
    def initializer_list_opt(self, p):
        return p.initializer_list

    @_("empty")
    def initializer_list_opt(self, p):
        return []


    
    # ------------------------------------------------------------
    #<initializer_list> ::= <initializer>
    #                 | <initializer_list> "," <initializer>
    @_("initializer_list COMMA initializer")
    def initializer_list(self, p):
        return p.initializer_list + [p.initializer]

    @_("initializer")
    def initializer_list(self, p):
        return [p.initializer]
    


    # ------------------------------------------------------------
    #<declarator> ::= <identifier>
    #           | "(" <declarator> ")"
    @_('ID')
    def declarator(self, p):
        return ID(name=p.ID, coord=self._token_coord(p._slice[0]))
    
    @_("LPAREN declarator RPAREN")
    def declarator(self, p):
        return p.declarator
    

    
    # ------------------------------------------------------------
    # <parameter_declaration> ::= <type_specifier> <declarator>
    @_("type_specifier declarator")
    def parameter_declaration(self, p):
        return ParamDecl(
            type = p.type_specifier,
            name = p.declarator,
            coord = self._token_coord(p._slice[0])
        )
    
    # ------------------------------------------------------------   
    #<parameter_list> ::= <parameter_declaration>
    #               | <parameter_list> "," <parameter_declaration> 
    @_("parameter_list COMMA parameter_declaration")
    def parameter_list(self, p):
        return ParamList(params=p.parameter_list.params + [p.parameter_declaration])

    @_("parameter_declaration")
    def parameter_list(self, p):
        return ParamList(params=[p.parameter_declaration])

    
    
    # ------------------------------------------------------------
    # <type_specifier> ::= "void"| "boolean"| "char"| "int"| "String"| "char" "[" "]"| "int" "[" "]"| <identifier>
    @_("VOID")
    def type_specifier(self, p):
        return Type(name="void", coord=self._token_coord(p._slice[0]))

    @_("BOOLEAN")
    def type_specifier(self, p):
        return Type(name="boolean", coord=self._token_coord(p._slice[0]))

    @_("CHAR")
    def type_specifier(self, p):
        return Type(name="char", coord=self._token_coord(p._slice[0]))

    @_("INT")
    def type_specifier(self, p):
        return Type(name="int", coord=self._token_coord(p._slice[0]))

    @_("STRING")
    def type_specifier(self, p):
        return Type(name="String", coord=self._token_coord(p._slice[0]))

    @_("CHAR LBRACK RBRACK")
    def type_specifier(self, p):
        return Type(name="char[]", coord=self._token_coord(p._slice[0]))
    
    @_("INT LBRACK RBRACK")
    def type_specifier(self, p):
        return Type(name="int[]", coord=self._token_coord(p._slice[0]))
    
    @_("ID")
    def type_specifier(self, p):
        return Type(
            name=ID(p.ID, coord=self._token_coord(p._slice[0])),
            coord=self._token_coord(p._slice[0])
        )

    
    # ------------------------------------------------------------
    # <expression> ::= <assignment_expression>
    #                | <expression> "," <assignment_expression>
    @_('expression COMMA assignment_expression')
    def expression(self, p):
        if isinstance(p.expression, ExprList):
            return ExprList((p.expression.exprs + [p.assignment_expression]), coord=self._token_coord(p._slice[0]))
        else:
            return ExprList(([p.expression, p.assignment_expression]), coord=self._token_coord(p._slice[0]))

    @_('assignment_expression')
    def expression(self, p):
        return p.assignment_expression


    # ------------------------------------------------------------
    # <assignment_expression> ::= <binary_expression>
    #                       | <unary_expression> "=" <assignment_expression>
    # Atribuição
    @_("binary_expression")
    def assignment_expression(self, p):
        return p.binary_expression

    @_('unary_expression ASSIGN assignment_expression')
    def assignment_expression(self, p):
        return Assignment(
            op=p.ASSIGN,
            lvalue=p.unary_expression, 
            rvalue=p.assignment_expression, coord=self._token_coord(p._slice[0]))
    


    # <binary_expression> ::= <unary_expression>
    #    | <binary_expression> "*" <binary_expression>  | <binary_expression> "/" <binary_expression>
    #    | <binary_expression> "%" <binary_expression>  | <binary_expression> "+" <binary_expression>
    #    | <binary_expression> "-" <binary_expression>  | <binary_expression> "<" <binary_expression>
    #    | <binary_expression> "<=" <binary_expression> | <binary_expression> ">" <binary_expression>
    #    | <binary_expression> ">=" <binary_expression> | <binary_expression> "==" <binary_expression>
    #    | <binary_expression> "!=" <binary_expression> | <binary_expression> "&&" <binary_expression>
    #    | <binary_expression> "||" <binary_expression>
    
    @_("unary_expression")
    def binary_expression(self, p):
        return p.unary_expression

    def buildBinaryOPTION(self, p, op):
        return BinaryOp(
            op = op,
            left = p.binary_expression0, 
            right = p.binary_expression1,
            coord  = self._token_coord(p._slice[0])
        )
    
    @_("binary_expression TIMES binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "*")
    
    @_("binary_expression DIVIDE binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "/")

    @_("binary_expression MOD binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "%")
    
    @_("binary_expression PLUS binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "+")
    
    @_("binary_expression MINUS binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "-")
    
    @_("binary_expression LT binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "<")
    
    @_("binary_expression LE binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "<=")
    
    @_("binary_expression GT binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, ">")
    
    @_("binary_expression GE binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, ">=")
    
    @_("binary_expression EQ binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "==")
    
    @_("binary_expression NE binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "!=")

    @_("binary_expression AND binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "&&")
    
    @_("binary_expression OR binary_expression")
    def binary_expression(self, p):
        return self.buildBinaryOPTION(p, "||")
    

    # ------------------------------------------------------------
    # <unary_expression> ::= <postfix_expression>
    #                  | <unary_operator> <unary_expression>
    @_("postfix_expression")
    def unary_expression(self, p):
        return p.postfix_expression
    
    @_("unary_operator unary_expression")
    def unary_expression(self, p):
        return UnaryOp(
            op= p.unary_operator, 
            expr= p.unary_expression, 
            coord = self._token_coord(p._slice[0])
        )

    # ------------------------------------------------------------
    # <unary_operator> ::= "+" | "-" | "!"
    @_("PLUS")
    def unary_operator(self, p):
        return "+"
    
    @_("MINUS")
    def unary_operator(self, p):
        return "-"
    
    @_("NOT")
    def unary_operator(self, p):
        return "!"

    # ------------------------------------------------------------
    #<postfix_expression> ::= <primary_expression>
    #                   | <postfix_expression> "." "length"
    #                   | <postfix_expression> "." <identifier>
    #                   | <postfix_expression> "." <identifier> "(" {<argument_expression>}? ")"
    #                   | <postfix_expression> "[" <expression> "]"
    @_("primary_expression")
    def postfix_expression(self, p):
        return p.primary_expression
    
    @_("postfix_expression DOT LENGTH")
    def postfix_expression(self, p):
        #print("PRINTTTTTT 1: ",p.postfix_expression)
        return Length(
            expr = p.postfix_expression,
            #field_name = "length",
            coord = self._token_coord(p._slice[0])
        )
    
    @_("postfix_expression DOT identifier")
    def postfix_expression(self, p):
        #print("PRINTTTTTT 2: ",p.postfix_expression.name)
        return FieldAccess(
            object = p.postfix_expression,
            field_name = p.identifier,
            coord = self._token_coord(p._slice[0])
        )

    @_("postfix_expression DOT identifier LPAREN argument_expression RPAREN ")
    def postfix_expression(self, p):
        if(len(p.argument_expression) > 1):
            return MethodCall(
                object= p.postfix_expression,
                method_name = p.identifier,
                args = ExprList(exprs = p.argument_expression, coord = self._token_coord(p._slice[4])),
                coord=self._token_coord(p._slice[0])
            )
        else:
            return MethodCall(
                object= p.postfix_expression,
                method_name = p.identifier,
                args = p.argument_expression[0],
                coord=self._token_coord(p._slice[0])
            )


    @_("postfix_expression DOT identifier LPAREN RPAREN ")
    def postfix_expression(self, p):
        return MethodCall(
            object= p.postfix_expression,
            method_name = p.identifier,
            args = None,
            coord=self._token_coord(p._slice[0])
        )

    @_("postfix_expression LBRACK expression RBRACK")
    def postfix_expression(self, p):
        return ArrayRef(
            name=p.postfix_expression,
            subscript=p.expression,
            coord=self._token_coord(p._slice[0])
        )    

    # ------------------------------------------------------------
    #<primary_expression> ::= <identifier>
    #    | <constant> | <this_expression>
    #    | <new_expression>| "(" <expression> ")"
    @_("identifier")
    def primary_expression(self, p):
        return p.identifier
    
    @_("constant")
    def primary_expression(self, p):
        return p.constant
    
    @_("this_expression")
    def primary_expression(self, p):
        return p.this_expression
    
    @_("new_expression")
    def primary_expression(self, p):
        return p.new_expression    

    @_("LPAREN expression RPAREN")
    def primary_expression(self, p):
        return p.expression
    
    
    # ------------------------------------------------------------
    #<argument_expression> ::= <assignment_expression>
    #                    | <argument_expression> "," <assignment_expression>
    @_("argument_expression COMMA assignment_expression")
    def argument_expression(self, p):
        return p.argument_expression + [p.assignment_expression]

    @_("assignment_expression")
    def argument_expression(self, p):
        return [p.assignment_expression]
        
    # ------------------------------------------------------------
    #<constant> ::= <boolean_literal> | <CHAR_LITERAL> 
    #            | <INT_LITERAL> | <STRING_LITERAL>
    @_("boolean_literal")
    def constant(self, p):
        return p.boolean_literal

    @_("CHAR_LITERAL")
    def constant(self, p):
        return Constant(type="char", value=p.CHAR_LITERAL, coord=self._token_coord(p._slice[0]))


    @_("INT_LITERAL")
    def constant(self, p):
        return Constant(type="int", value=int(p.INT_LITERAL), coord=self._token_coord(p._slice[0]))

    @_("STRING_LITERAL")
    def constant(self, p):
        return Constant(type="String", value=str(p.STRING_LITERAL), coord=self._token_coord(p._slice[0]))


    #<boolean_literal> ::= "true" | "false"
    @_("TRUE")
    def constant(self, p):
        return Constant(type="boolean", value="true", coord=self._token_coord(p._slice[0]))

    @_("FALSE")
    def constant(self, p):
        return Constant(type="boolean", value="false", coord=self._token_coord(p._slice[0]))



    # ------------------------------------------------------------
    # <this_expression> ::= "this"
    @_("THIS")
    def this_expression(self, p):
        return This(coord=self._token_coord(p._slice[0]))

    
    # ------------------------------------------------------------
    #<new_expression> ::= "new" "char" "[" <expression> "]"
    #               | "new" "int" "[" <expression> "]"
    #               | "new" <identifier> "(" ")"
    @_("NEW CHAR LBRACK expression RBRACK")
    def new_expression(self, p):
        return NewArray(
            type=Type(name="char[]"), 
            size=p.expression, 
            coord=self._token_coord(p._slice[0])
        )

    @_("NEW INT LBRACK expression RBRACK")
    def new_expression(self, p):
        return NewArray(
            type=Type(name="int[]"),
            size=p.expression, 
            coord=self._token_coord(p._slice[0]))

    @_("NEW identifier LPAREN RPAREN")
    def new_expression(self, p):
        return NewObject(
            type=Type(name=p.identifier, coord=self._token_coord(p._slice[1])),
            coord=self._token_coord(p._slice[0])
    )

    # ------------------------------------------------------------
    # <identifier> ::= <ID>
    @_("ID")
    def identifier(self, p):
        return ID(name=p.ID, coord = self._token_coord(p._slice[0]))

    
    # ------------------------------------------------------------
    #<statement> ::= 
    #         <compound_statement> | <expresssion_statement>
    #          | <if_statement>    | <while_statement>
    #          | <for_statement>   | <assert_statement>
    #          | <print_statement> | <jump_statement>
    @_("compound_statement")
    def statement(self, p):
        return p.compound_statement
    
    @_("expression_statement")
    def statement(self, p):
        return p.expression_statement

    @_("if_statement")
    def statement(self, p):
        return p.if_statement

    @_("while_statement")
    def statement(self, p):
        return p.while_statement

    @_("for_statement")
    def statement(self, p):
        return p.for_statement

    @_("assert_statement")
    def statement(self, p):
        return p.assert_statement

    @_("print_statement")
    def statement(self, p):
        return p.print_statement

    @_("jump_statement")
    def statement(self, p):
        return p.jump_statement

    # ------------------------------------------------------------
    ##<compound_statement> ::= "{" {<compound_declaration>}* {<statement>}* "}"
    @_("LBRACE compound_declaration_kstar statement_kstar RBRACE")
    def compound_statement(self, p):
        declarations = []
        for decl_list in p.compound_declaration_kstar:
            declarations += decl_list.decls
        
        #print(f"Declarations: {declarations}")  # Print para ver as declarações
        #print(f"Statements: {p.statement_kstar}")  # Print para ver os statements
        return Compound(
            statements=declarations + p.statement_kstar,
            coord=self._token_coord(p._slice[0])
        )


    @_("compound_declaration_kstar compound_declaration")
    def compound_declaration_kstar(self, p):
        return p.compound_declaration_kstar + [p.compound_declaration]
        

    @_("empty")
    def compound_declaration_kstar(self, p):
        return []
    

    @_("statement_kcross")
    def statement_kstar(self, p):
        return p.statement_kcross
    
    @_("")
    def statement_kstar(self, p):
        return []
  
    
    @_("statement_kcross statement")
    def statement_kcross(self, p):
        return p.statement_kcross + [p.statement]

    @_("statement")
    def statement_kcross(self, p):
        return [p.statement]


  

    # ------------------------------------------------------------
    # <expresssion_statement> ::= <expression> ";"
    @_("expression SEMICOLON")
    def expression_statement(self, p):
        return p.expression

    # ------------------------------------------------------------
    # <if_statement> ::= "if" "(" <expression> ")" <statement>
    #              | "if" "(" <expression> ")" <statement> "else" <statement>
    @_("IF LPAREN expression RPAREN statement ELSE statement")
    def if_statement(self, p):
        return If(
            cond = p.expression, 
            iftrue = p.statement0,
            iffalse = p.statement1,
            coord = self._token_coord(p._slice[0])
        )
    
    @_("IF LPAREN expression RPAREN statement")
    def if_statement(self, p):
        return If(
            cond = p.expression, 
            iftrue = p.statement,
            iffalse = None,
            coord = self._token_coord(p._slice[0])
        
    )
    
    # ------------------------------------------------------------
    # <while_statement> ::= "while" "(" <expression> ")" <statement>
    @_("WHILE LPAREN expression RPAREN statement")
    def while_statement(self, p):
        return While(
            cond = p.expression,
            body = p.statement,
            coord = self._token_coord(p._slice[0])
        )
    
    # ------------------------------------------------------------
    # <for_statement> ::= "for" "(" {<expression>}? ";" {<expression>}? ";" {<expression>}? ")" <statement>
    #               | "for" "(" <compound_declaration> {<expression>}? ";" {<expression>}? ")" <statement>
    @_("FOR LPAREN expression_opt SEMICOLON expression_opt SEMICOLON expression_opt RPAREN statement")
    def for_statement(self, p):
        return For(
            init=p.expression_opt0,  
            cond=p.expression_opt1,
            next=p.expression_opt2,
            body=p.statement,
            coord=self._token_coord(p._slice[0])
        )

    
    @_("FOR LPAREN compound_declaration expression_opt SEMICOLON expression_opt RPAREN statement")
    def for_statement(self, p):
        decllist = p.compound_declaration
        decllist.coord = self._token_coord(p._slice[0])
        return For(
            init=p.compound_declaration,  # isso sim pode ser uma DeclList
            cond=p.expression_opt0,
            next=p.expression_opt1,
            body=p.statement,
            coord=self._token_coord(p._slice[0])
        )


    # expression ? - expression_opt
    @_("expression")
    def expression_opt(self, p):
        return p.expression

    @_("empty")
    def expression_opt(self, p):
        return None

    # ------------------------------------------------------------
    # <assert_statement> ::= "assert" <expression> ";"
    @_("ASSERT expression SEMICOLON")
    def assert_statement(self, p):
        return Assert(expr=p.expression, coord=self._token_coord(p._slice[0]))

    # ------------------------------------------------------------
    # <print_statement> ::= "print" "(" {<expression>}? ")" ";"
    @_("PRINT LPAREN expression_opt RPAREN SEMICOLON")
    def print_statement(self, p):
        return Print(expr=p.expression_opt, coord=self._token_coord(p._slice[0]))
    
    # ------------------------------------------------------------
    # <jump_statement> ::= "break" ";"
    #                 | "return" {<expression>}? ";
    @_("BREAK SEMICOLON")
    def jump_statement(self, p):
        return Break(coord=self._token_coord(p._slice[0]))

    @_("RETURN expression_opt SEMICOLON")
    def jump_statement(self, p):
        return Return(expr=p.expression_opt, coord=self._token_coord(p._slice[0]))

    
    # ------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------
    def error(self, p):
        if p:
            self._parser_error(
                "Before %s" % p.value, Coord(p.lineno, self.mjlex.find_tok_column(p))
            )
        else:
            self._parser_error("At the end of input (%s)" % self.mjlex.filename)


def main():
    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Path to file to be parsed", type=str)
    args = parser.parse_args()

    # get input path
    input_file = args.input_file
    input_path = pathlib.Path(input_file)

    # check if file exists
    if not input_path.exists():
        print("ERROR: Input", input_path, "not found", file=sys.stderr)
        sys.exit(1)

    parser = MJParser()

    # open file and print ast
    with open(input_path) as f:
        ast = parser.parse(f.read())
        print(parser.log.text)
        ast.show(buf=sys.stdout, showcoord=True)


if __name__ == "__main__":
    main()
