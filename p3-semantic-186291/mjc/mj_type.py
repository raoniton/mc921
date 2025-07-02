class MJType:
    """
    Class that represents a type in the MiniJava language.  Basic
    Types are declared as singleton instances of this type.
    """

    def __init__(
        self, name, binary_ops=set(), unary_ops=set(), rel_ops=set(), assign_ops=set()
    ):
        """
        You must implement yourself and figure out what to store.
        """
        self.typename = name
        self.unary_ops = unary_ops
        self.binary_ops = binary_ops
        self.rel_ops = rel_ops
        self.assign_ops = assign_ops

    def __str__(self):
        return f"type({self.typename})"


# Create specific instances of basic types. You will need to add
# appropriate arguments depending on your definition of MJType

BooleanType = MJType(
    name="boolean",
    binary_ops={},
    unary_ops={"!"},
    rel_ops={"==", "!="},
    assign_ops={"="},
)

CharArrayType = MJType(
    name="char[]",
    binary_ops={"+"},
    unary_ops=set(),
    rel_ops={"==", "!="},
    assign_ops={"="},
)

CharType = MJType(
    name="char",
    binary_ops={"-", "*", "/", "%"},
    unary_ops={"-", "+"},
    rel_ops={"==", "!=", "<", ">", "<=", ">="},
    assign_ops={"="},
)

IntArrayType = MJType(
    name="int[]",
    binary_ops=set(),
    unary_ops=set(),
    rel_ops={"==", "!="},
    assign_ops={"="},
)

IntType = MJType(
    name="int",
    binary_ops={"+", "-", "*", "/", "%"},
    unary_ops={"-", "+"},
    rel_ops={"==", "!=", "<", ">", "<=", ">="},
    assign_ops={"="},
)

StringType = MJType(
    name="String",
    binary_ops={"+", "=="},
    unary_ops=set(),
    rel_ops={"==", "!="},
    assign_ops={"="},
)

StringArrayType = MJType(
    name="String[]",
    binary_ops=set(),
    unary_ops=set(),
    rel_ops={"==", "!="},
    assign_ops={"="},
)


VoidType = MJType(
    name="void",
    binary_ops=set(),
    unary_ops=set(),
    rel_ops=set(),
    assign_ops=set(),
)


# Array & Object types need to be instantiated for each declaration
class ArrayType(MJType):
    def __init__(self, array_type: str, element_type: str, size=None):
        """
        :param array_type: Type of the array (int[] or char[])
        :param element_type: Type of the array elements (int or char)
        :param size: Integer with the length of the array.
        """
        self.size = size
        self.element_type = element_type
        super().__init__(name=array_type, rel_ops={"==", "!="}, assign_ops={"="})


class ObjectType(MJType):
    def __init__(self, class_name):
        self.class_name = class_name,
        #rel_ops={"==", "!="},
        super().__init__(name=class_name, rel_ops={"==","!="}, assign_ops={"="})
    
    def __is_assignable_to(self, other):
        #if the objects are equal, is possible do assigments "="
        if self == other:
            return True
        
        #if they are instances of ObjectType, we return class_name
        if isinstance(self, ObjectType) and isinstance(other, ObjectType):
            return self.class_name == other.class_name
    
    def __eq__(self, other):
        if not isinstance(other, MJType):
            return False
        return self.typename == other.typename


class MethodType(MJType):
    def __init__(self, return_type, param_types):
        
        #:param return_type: Um objeto MJType representando o tipo de retorno do método
        #:param param_types: Uma lista de MJType representando os tipos dos parâmetros
        
        self.return_type = return_type
        self.param_types = param_types
        super().__init__(name="method")

    def __str__(self):
        params = ", ".join(str(p) for p in self.param_types)
        return f"method({self.return_type} ({params}))"

    def __eq__(self, other):
        if not isinstance(other, MethodType):
            return False
        return (
            self.return_type == other.return_type
            and self.param_types == other.param_types
        )
