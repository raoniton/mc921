import sys
from abc import ABC, abstractmethod


def represent_node(obj, indent):
    def _repr(obj, indent, printed_set):
        """
        Get the representation of an object, with dedicated pprint-like format for lists.
        """
        if isinstance(obj, list):
            indent += 1
            sep = ",\n" + (" " * indent)
            final_sep = ",\n" + (" " * (indent - 1))
            return (
                "["
                + (sep.join((_repr(e, indent, printed_set) for e in obj)))
                + final_sep
                + "]"
            )
        elif isinstance(obj, Node):
            if obj in printed_set:
                return ""
            else:
                printed_set.add(obj)
            result = obj.__class__.__name__ + "("
            indent += len(obj.__class__.__name__) + 1
            attrs = []

            # convert each node attribute to string
            for name, value in vars(obj).items():

                # is an irrelevant attribute: skip it.
                if name in ("bind", "coord"):
                    continue

                # relevant attribte not set: skip it.
                if value is None:
                    continue

                # relevant attribute set: append string representation.
                value_str = _repr(value, indent + len(name) + 1, printed_set)
                attrs.append(name + "=" + value_str)

            sep = ",\n" + (" " * indent)
            final_sep = ",\n" + (" " * (indent - 1))
            result += sep.join(attrs)
            result += ")"
            return result
        elif isinstance(obj, str):
            return obj
        else:
            return str(obj)

    # avoid infinite recursion with printed_set
    printed_set = set()
    return _repr(obj, indent, printed_set)


#
# Node coordinates (code position)
#
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
            coord_str = f"@ {self.line}:{self.column}"
        elif self.line:
            coord_str = f"@ {self.line}"
        else:
            coord_str = ""
        return coord_str


#
# ABSTRACT NODES
#
class Node(ABC):
    """Abstract base class for AST nodes."""

    attr_names = ()

    @abstractmethod
    def __init__(self, coord: Coord = None):
        """
        :param coord: code position.
        """
        self.coord = coord

    def __repr__(self):
        """Generates a python representation of the current node"""
        return represent_node(self, 0)

    def children(self):
        """A sequence of all children that are Nodes"""
        pass

    def show(
        self,
        buf=sys.stdout,
        offset=0,
        attrnames=False,
        nodenames=False,
        showcoord=False,
        _my_node_name=None,
    ):
        """Pretty print the Node and all its attributes and children (recursively) to a buffer.
        buf:
            Open IO buffer into which the Node is printed.
        offset:
            Initial offset (amount of leading spaces)
        attrnames:
            True if you want to see the attribute names in name=value pairs. False to only see the values.
        nodenames:
            True if you want to see the actual node names within their parents.
        showcoord:
            Do you want the coordinates of each Node to be displayed.
        """
        lead = " " * offset
        if nodenames and _my_node_name is not None:
            buf.write(lead + self.__class__.__name__ + " <" + _my_node_name + ">: ")
            inner_offset = len(self.__class__.__name__ + " <" + _my_node_name + ">: ")
        else:
            buf.write(lead + self.__class__.__name__ + ":")
            inner_offset = len(self.__class__.__name__ + ":")

        if self.attr_names:
            if attrnames:
                nvlist = [
                    (
                        n,
                        represent_node(
                            getattr(self, n), offset + inner_offset + 1 + len(n) + 1
                        ),
                    )
                    for n in self.attr_names
                    if getattr(self, n) is not None
                ]
                attrstr = ", ".join("%s=%s" % nv for nv in nvlist)
            else:
                vlist = [getattr(self, n) for n in self.attr_names]
                attrstr = ", ".join(
                    represent_node(v, offset + inner_offset + 1) for v in vlist
                )
            buf.write(" " + attrstr)

        if showcoord:
            if self.coord and self.coord.line != 0:
                buf.write(" %s" % self.coord)
        buf.write("\n")

        for child_name, child in self.children():
            child.show(buf, offset + 4, attrnames, nodenames, showcoord, child_name)


class Expr(Node):
    """Node representing an Expression"""

    pass


class Statement(Node):
    """Node representing an Statement"""

    pass


#
# CONCRETE NODES
#


class ID(Node):
    """Node representing an identifier"""

    attr_names = ("name",)

    def __init__(self, name: str, coord: Coord = None):
        """
        :param name: ID unique name.
        :param coord: code position.
        """
        self.name = name
        self.coord = coord

    def children(self):
        return ()


class Type(Node):
    """Node representing a type specifier"""

    attr_names = ("name",)

    def __init__(self, name: str, coord: Coord = None):
        """
        :param name: type name (int, char, ...).
        :param coord: code position.
        """
        self.name = name
        self.coord = coord

    def children(self):
        return ()


# Declarations


class VarDecl(Node):
    """Node that represents a variable declaration"""

    attr_names = ("name",)

    def __init__(self, type: Type, name: ID, init, coord: Coord = None):
        """
        :param type: variable primitive type.
        :param name: variable name.
        :param init: initialization value.
        :param coord: code position.
        """
        self.type = type
        self.name = name
        self.init = init
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None:
            nodelist.append(("type", self.type))
        if self.init is not None:
            nodelist.append(("init", self.init))
        return tuple(nodelist)

    @property
    def identifier(self):
        """I get the declaration ID node"""
        return self.declname

    @identifier.setter
    def identifier(self, identifier):
        """
        I set the declaration ID node.

        :param identifier: AST ID node.
        """
        self.declname = identifier

    def modify(self, modifier):
        """I modify this declaration.

        :para modifier: declaration modifier node.

        :returns: modified variable declaration.
        """
        modifier.type = self
        return modifier

    @property
    def primitive(self):
        """I get the declaration primitive type."""
        return self.type

    @primitive.setter
    def primitive(self, typeNode):
        """I set the declaration underlying primitive type.

        :param typeNode: primitive type node to be set.
        """
        self.type = typeNode


class ParamDecl(Node):
    """Node representing a parameter declaration"""

    attr_names = ("name",)

    def __init__(self, type: Type, name: ID, coord: Coord = None):
        """
        :param type: variable primitive type.
        :param name: variable name.
        :param coord: code position.
        """
        self.type = type
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None:
            nodelist.append(("type", self.type))
        return tuple(nodelist)


class DeclList(Node):
    """Node representing a list of var declarations"""

    attr_names = ()

    def __init__(self, decls: list[VarDecl], coord: Coord = None):
        """
        :param decls: list of declarations.
        :param coord: code position.
        """
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.decls or []):
            nodelist.append(("decls[%d]" % i, child))
        return tuple(nodelist)


class ParamList(Node):
    """Node representing a list of parameters"""

    attr_names = ()

    def __init__(self, params: list[ParamDecl], coord: Coord = None):
        """
        I create an instance of this class.

        :param params: list of parameter declarations.
        :param coord: code position.
        """
        self.params = params
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.params or []):
            nodelist.append(("params[%d]" % i, child))
        return tuple(nodelist)


# Expressions


class ExprList(Node):
    """Node representing a list of expressions"""

    attr_names = ()

    def __init__(self, exprs: list[Expr], coord: Coord = None):
        """
        I create an instance of this class.

        :param exprs: list of expressions.
        :param coord: code position.
        """
        self.exprs = exprs
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.exprs or []):
            nodelist.append(("exprs[%d]" % i, child))
        return tuple(nodelist)


class ArrayRef(Expr):
    """Node representing an access to a position in an array"""

    attr_names = ()

    def __init__(self, name, subscript, coord: Coord = None):
        """
        :param name: name of the array being accessed.
        :param subscript: dimension of the array.
        :param coord: declaration code position.
        """
        self.name = name
        self.subscript = subscript
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None:
            nodelist.append(("name", self.name))
        if self.subscript is not None:
            nodelist.append(("subscript", self.subscript))
        return tuple(nodelist)


class Assignment(Expr):
    """Node representing an Assigment Expression"""

    attr_names = ("op",)

    def __init__(self, op: str, lvalue: Expr, rvalue: Expr, coord: Coord = None):
        """
        :param op: assignment operator (=, +=, %=, ...).
        :param lvalue: variable being written.
        :param rvalue: value being assingned to variable.
        :param coord: code position.
        """
        self.op = op
        self.lvalue = lvalue
        self.rvalue = rvalue
        self.coord = coord

    def children(self):
        nodelist = []
        if self.lvalue is not None:
            nodelist.append(("lvalue", self.lvalue))
        if self.rvalue is not None:
            nodelist.append(("rvalue", self.rvalue))
        return tuple(nodelist)


class BinaryOp(Expr):
    "Node representing a Binary Expression."

    attr_names = ("op",)

    def __init__(self, op: str, left: Expr, right: Expr, coord: Coord = None):
        """
        :param op: binary operator (+, -, *, ...).
        :param left: left hand side expression.
        :param right: right hand side expression.
        :param coord: code position.
        """
        self.op = op
        self.lvalue = left
        self.rvalue = right
        self.coord = coord

    def children(self):
        nodelist = []
        if self.lvalue is not None:
            nodelist.append(("lvalue", self.lvalue))
        if self.rvalue is not None:
            nodelist.append(("rvalue", self.rvalue))
        return tuple(nodelist)


class UnaryOp(Expr):
    """Node representing a unary expression"""

    attr_names = ("op",)

    def __init__(self, op: str, expr: Expr, coord: Coord = None):
        """
        :param op: unary operator (!, +, -)
        :param expr: expression whose value will be modified by the operator.
        """
        self.op = op
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None:
            nodelist.append(("expr", self.expr))
        return tuple(nodelist)


class Constant(Expr):
    "Node representing a constant"

    attr_names = ("type", "value")

    def __init__(self, type: str, value, coord: Coord = None):
        """
        :param type: constant type.
        :param value: constant value.
        :param coord: code position.
        """
        self.type = type
        self.value = value
        self.coord = coord

    def children(self):
        return ()


class FieldAccess(Expr):
    """Node representing access to a field of an object"""

    attr_names = ()

    def __init__(
        self,
        object: Expr,
        field_name: ID,
        coord: Coord = None,
    ):
        """
        :param object: object being accessed.
        :param field_name: field being accessed.
        """
        self.object = object
        self.field_name = field_name
        self.coord = coord

    def children(self):
        nodelist = []
        if self.object is not None:
            nodelist.append(("object", self.object))
        if self.field_name is not None:
            nodelist.append(("field_name", self.field_name))
        return tuple(nodelist)


class MethodCall(Expr):
    """node representing the invocation of a method"""

    attr_names = ()

    def __init__(
        self,
        object: ID,
        method_name: ID,
        args: ExprList,
        coord: Coord = None,
    ):
        """
        :param object: object on which the method will be called.
        :param method_name: name of the method being invoked.
        :param args: arguments passed to the method.
        """
        self.object = object
        self.method_name = method_name
        self.args = args
        self.coord = coord

    def children(self):
        nodelist = []
        if self.object is not None:
            nodelist.append(("object", self.object))
        if self.method_name is not None:
            nodelist.append(("method_name", self.method_name))
        if self.args is not None:
            nodelist.append(("args", self.args))
        return tuple(nodelist)


class This(Expr):
    """Node representing the 'this' expression"""

    def __init__(self, coord: Coord = None):
        self.coord = coord

    def children(self):
        return ()


class Length(Expr):
    """Node representing access to the length of an array or string"""

    attr_names = ()

    def __init__(self, expr: Expr, coord: Coord = None):
        """
        :param expr: object whose length will be accessed.
        """
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None:
            nodelist.append(("expr", self.expr))
        return tuple(nodelist)


class NewArray(Expr):
    """Expression representing a New Array allocation."""

    attr_names = ()

    def __init__(self, type: Type, size: Expr, coord: Coord = None):
        """
        :param type: Array type (char[] or int[]).
        :param size: Array size.
        :param coord: code position.
        """
        self.type = type
        self.size = size
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None:
            nodelist.append(("type", self.type))
        if self.size is not None:
            nodelist.append(("size", self.size))
        return tuple(nodelist)


class NewObject(Expr):
    """Node representing a New Object allocation."""

    attr_names = ()

    def __init__(self, type: Type, coord: Coord = None):
        """
        :param type: yype of the object.
        :param coord: code position.
        """
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None:
            nodelist.append(("type", self.type))
        return tuple(nodelist)


# Statements


class Assert(Statement):
    """Node representing an Assert statment"""

    attr_names = ()

    def __init__(self, expr: Expr, coord: Coord = None):
        """
        :param expr: boolean expression being asserted.
        :param coord: code position.
        """
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None:
            nodelist.append(("expr", self.expr))
        return tuple(nodelist)


class Compound(Statement):
    """Node representing the Compound Statement (block of code)"""

    attr_names = ()

    def __init__(self, staments: list[Statement], coord: Coord = None):
        """
        :param staments: statements within the compound.
        :param coord: code position.
        """
        self.staments = staments
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.staments or []):
            nodelist.append(("staments[%d]" % i, child))
        return tuple(nodelist)


class For(Statement):
    """Node representing the For statement"""

    attr_names = ()

    def __init__(
        self,
        init: DeclList,
        cond: Expr,
        next: Expr,
        body: Statement,
        coord: Coord = None,
    ):
        """
        :param init: initialization to be made before the loop.
        :param cond: conditional to be evaluated each iteration.
        :param next: computation to be made after each iteration.
        :param body: statements within the loop's body.
        :param coord: code position.
        """
        self.init = init
        self.cond = cond
        self.next = next
        self.body = body
        self.coord = coord

    def children(self):
        nodelist = []
        if self.init is not None:
            nodelist.append(("init", self.init))
        if self.cond is not None:
            nodelist.append(("cond", self.cond))
        if self.next is not None:
            nodelist.append(("next", self.next))
        if self.body is not None:
            nodelist.append(("body", self.body))
        return tuple(nodelist)


class While(Statement):
    """Node representing the While statement"""

    attr_names = ()

    def __init__(self, cond: Expr, body: Statement, coord: Coord = None):
        """
        :param cond: conditional being evaluated at every iteration.
        :param body: compound representing the loop body.
        :param coord: code position.
        """
        self.cond = cond
        self.body = body
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None:
            nodelist.append(("cond", self.cond))
        if self.body is not None:
            nodelist.append(("body", self.body))
        return tuple(nodelist)


class If(Statement):
    """Node representing the If statement"""

    attr_names = ()

    def __init__(
        self, cond: Expr, iftrue: Statement, iffalse: Statement, coord: Coord = None
    ):
        """
        :param cond: conditional statement being evaluated.
        :param iftrue: compound block to execute on true statement.
        :param iffalse: compound block to execute on false statement.
        :param coord: code position.
        """
        self.cond = cond
        self.iftrue = iftrue
        self.iffalse = iffalse
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None:
            nodelist.append(("cond", self.cond))
        if self.iftrue is not None:
            nodelist.append(("iftrue", self.iftrue))
        if self.iffalse is not None:
            nodelist.append(("iffalse", self.iffalse))
        return tuple(nodelist)


class Print(Statement):
    """Node represeting the Print statement"""

    attr_names = ()

    def __init__(self, expr: Expr | ExprList, coord: Coord = None):
        """
        :param expr: expression to be printed.
        :param coord: code position.
        """
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None:
            nodelist.append(("expr", self.expr))
        return tuple(nodelist)


class Return(Statement):
    """Node representing the Return statement"""

    attr_names = ()

    def __init__(self, expr: Expr, coord: Coord = None):
        """
        :param expr: expression whose result will be returned.
        :param coord: code position.
        """
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None:
            nodelist.append(("expr", self.expr))
        return tuple(nodelist)


class Break(Statement):
    "Node representing the break statement"

    attr_names = ()

    def __init__(self, coord: Coord = None):
        self.coord = coord

    def children(self):
        return ()


class InitList(Node):
    """Node representing a list of variable initializers"""

    attr_names = ()

    def __init__(self, exprs: list[Expr], coord: Coord = None):
        """
        :param exprs: list of initializer expressions.
        :param coord: code position.
        """
        self.exprs = exprs
        self.coord = coord
        self.value = None

    def children(self):
        nodelist = []
        for i, child in enumerate(self.exprs or []):
            nodelist.append(("exprs[%d]" % i, child))
        return tuple(nodelist)


class MethodDecl(Node):
    """Node representing the declaration of a regular method"""

    attr_names = ("name",)

    def __init__(
        self,
        type: Type,
        name: ID,
        param_list: ParamList,
        body: Compound,
        coord: Coord = None,
    ):
        """
        :param type: return type.
        :param name: method name.
        :param param_list: list of parameters
        :param body: statements within the Method's body.
        """
        self.type = type
        self.name = name
        self.param_list = param_list
        self.body = body
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None:
            nodelist.append(("type", self.type))
        if self.param_list is not None:
            nodelist.append(("params", self.param_list))
        if self.body is not None:
            nodelist.append(("body", self.body))
        return tuple(nodelist)


class MainMethodDecl(Node):
    """Node represeting the Main Method Declaration"""

    attr_names = ()

    def __init__(
        self,
        args: ID,
        body: Compound,
        coord: Coord = None,
    ):
        """
        :param args: list of arguments of the main method (String[] args).
        :param body: statements within the Main method.
        """
        self.args = args
        self.body = body
        self.coord = coord

    def children(self):
        nodelist = []
        if self.args is not None:
            nodelist.append(("args", self.args))
        if self.body is not None:
            nodelist.append(("body", self.body))
        return tuple(nodelist)


class Extends(Node):
    """Node representing inheritance between classes"""

    attr_names = ("super",)

    def __init__(self, super: ID, coord: Coord = None):
        """
        :param super: the class being inherited from (parent)
        """
        self.super = super
        self.coord = coord

    def children(self):
        return ()


class ClassDecl(Node):
    """Node representing a Class Declaration"""

    attr_names = ("name",)

    def __init__(
        self,
        name: ID,
        extends: ID,
        var_decls: list[VarDecl],
        method_decls: list[MethodDecl],
        coord: Coord = None,
    ):
        """
        :param name: Class name.
        :param extends: Name of the extended class.
        :param var_decls: List of var declarations.
        :param method_decls: List of method declarations.
        """
        self.name = name
        self.extends = extends
        self.var_decls = var_decls
        self.method_decls = method_decls
        self.coord = coord

    def children(self):
        decls = (
            ([self.extends] if self.extends is not None else [])
            + self.var_decls
            + self.method_decls
        )
        return tuple(((f"decls[{idx}]", decl) for idx, decl in enumerate(decls or [])))


class Program(Node):
    """Node that represent the MiniJava Program"""

    attr_names = ()

    def __init__(self, class_decls: list[ClassDecl], coord: Coord = None):
        """
        :param class_decls: program's class declarations.
        :param coord: code position.
        """
        self.class_decls = class_decls
        self.coord = coord

    def children(self):
        return tuple(
            (
                (f"class_decls[{idx}]", class_decl)
                for idx, class_decl in enumerate(self.class_decls or [])
            )
        )
