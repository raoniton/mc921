import sys
from enum import Enum, auto


# Custom exception for semantic errors
class SemanticError:
    def __init__(self, message, coord):
        self.message = message
        self.coord = coord

    def __str__(self):
        return f"SemanticError: {self.message} {self.coord}"


# Semantic Erros
class SemanticErrorType(Enum):
    UNDECLARED_NAME = auto()
    UNDECLARED_CLASS = auto()
    UNDECLARED_METHOD = auto()
    UNDECLARED_FIELD = auto()
    ALREADY_DECLARED_NAME = auto()
    ALREADY_DECLARED_CLASS = auto()
    ALREADY_DECLARED_METHOD = auto()
    ALREADY_DECLARED_FIELD = auto()
    ASSERT_EXPRESSION_TYPE_MISMATCH = auto()
    PRINT_EXPRESSION_TYPE_MISMATCH = auto()
    ASSIGN_TYPE_MISMATCH = auto()
    ARRAY_REF_TYPE_MISMATCH = auto()
    ARRAY_DIMENTION_MISMATCH = auto()
    ARRAY_ELEMENT_TYPE_MISMATCH = auto()
    BINARY_EXPRESSION_TYPE_MISMATCH = auto()
    UNSUPPORTED_BINARY_OPERATION = auto()
    WRONG_BREAK_STATEMENT = auto()
    ARGUMENT_COUNT_MISMATCH = auto()
    PARAMETER_TYPE_MISMATCH = auto()
    PARAMETER_ALREADY_DECLARED = auto()
    CONDITIONAL_EXPRESSION_TYPE_MISMATCH = auto()
    RETURN_TYPE_MISMATCH = auto()
    UNSUPPORTED_UNARY_OPERATION = auto()
    OBJECT_TYPE_MUST_BE_A_CLASS = auto()
    INVALID_LENGTH_TARGET = auto()
    NOT_A_CONSTANT = auto()


# Alias to SemanticErrorType
SE = SemanticErrorType


# Factory for creating semantic exceptions (Factory Method Pattern)
class SemanticErrorFactory:
    @staticmethod
    def create(
        error_type: SemanticErrorType, name: str = "", ltype: str = "", rtype: str = ""
    ) -> SemanticError:
        error_msgs = {
            SE.UNDECLARED_NAME: f"{name} is not defined",
            SE.UNDECLARED_CLASS: f"{name} is not a class type",
            SE.UNDECLARED_METHOD: f"{name} is not a class method",
            SE.UNDECLARED_FIELD: f"{name} is not defined in the class",
            SE.ALREADY_DECLARED_CLASS: f"{name} class has already been defined",
            SE.ALREADY_DECLARED_METHOD: f"{name} method has already been defined",
            SE.ALREADY_DECLARED_FIELD: f"Field {name} has already been defined",
            SE.PRINT_EXPRESSION_TYPE_MISMATCH: "Print expression must be of type(char), type(int) or type(String)",
            SE.ASSERT_EXPRESSION_TYPE_MISMATCH: "Assert expression must be of type(bool)",
            SE.ASSIGN_TYPE_MISMATCH: f"Cannot assign {rtype} to {ltype}",
            SE.ARRAY_REF_TYPE_MISMATCH: f"Cannot do an ArrayRef of {ltype}",
            SE.ARRAY_ELEMENT_TYPE_MISMATCH: f"{name} of {rtype} is incompatible with {ltype} of array",
            SE.BINARY_EXPRESSION_TYPE_MISMATCH: f"Binary operator {name} does not have matching LHS/RHS types",
            SE.UNSUPPORTED_BINARY_OPERATION: f"Binary operator {name} is not supported by {ltype}",
            SE.WRONG_BREAK_STATEMENT: "Break statement must be inside a loop",
            SE.ARRAY_DIMENTION_MISMATCH: f"Array dimension must be of type(int), not {ltype}",
            SE.ARGUMENT_COUNT_MISMATCH: f"Number of arguments to call {name} method mismatch",
            SE.PARAMETER_TYPE_MISMATCH: f"Type mismatch with parameter {name}",
            SE.PARAMETER_ALREADY_DECLARED: f"Parameter {name} has already been defined",
            SE.CONDITIONAL_EXPRESSION_TYPE_MISMATCH: f"conditional expression is {ltype}, not type(bool)",
            SE.RETURN_TYPE_MISMATCH: f"Return of {ltype} is incompatible with {rtype} method definition",
            SE.ALREADY_DECLARED_NAME: f"Name {name} is already defined in this scope",
            SE.UNSUPPORTED_UNARY_OPERATION: f"Unary operator {name} is not supported",
            SE.OBJECT_TYPE_MUST_BE_A_CLASS: f"The type of {name} must be a class",
            SE.INVALID_LENGTH_TARGET: "The target of the length operation must be of type array or String",
            SE.NOT_A_CONSTANT: f"Expression must be a constant",
        }

        return SemanticError(error_msgs[error_type], "")


# Semantic assert function that uses the factory to create and throw the exception
def assert_semantic(
    condition: bool,
    error_type: SemanticErrorType,
    coord: str,
    name: str = "",
    ltype: str = "",
    rtype: str = "",
):
    if not condition:
        semantic_error = SemanticErrorFactory.create(error_type, name, ltype, rtype)
        semantic_error.coord = coord
        print(semantic_error, file=sys.stdout)
        sys.exit(1)
