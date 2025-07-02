import argparse
import pathlib
import sys

from sly import Lexer


class MJLexer(Lexer):
    """A lexer for the Minijava language. After building it, set the
    input text, and call token() to get new
    tokens.
    """

    def __init__(self, error_func):
        self.error_func = error_func
        self.filename = ""

        # Keeps track of the last token returned from self.token()
        self.last_token = None

    def _error(self, msg, token):
        location = self._make_tok_location(token)
        self.error_func(msg, location[0], location[1])
        self.index += 1

    def find_tok_column(self, token):
        """Find the column of the token in its line."""
        last_cr = self.text.rfind("\n", 0, token.index)
        return token.index - last_cr

    def _make_tok_location(self, token):
        return (self.lineno, self.find_tok_column(token))

    # Error handling rule
    def error(self, t):
        msg = f"Illegal character {t.value[0]!r}"
        self._error(msg, t)

    def scan(self, data):
        output = ""
        for token in self.tokenize(data):
            token_str = (
                f"LexToken({token.type},{token.value!r},{token.lineno},{token.index})"
            )
            print(token_str)
            output += token_str + "\n"
        return output

    # Set of token names.
    tokens = {
        # Keywords
        "CLASS",
        "EXTENDS",
        "PUBLIC",
        "STATIC",
        "VOID",
        "MAIN",
        "STRING",
        "BOOLEAN",
        "CHAR",
        "INT",
        "IF",
        "ELSE",
        "WHILE",
        "FOR",
        "ASSERT",
        "BREAK",
        "RETURN",
        "NEW",
        "THIS",
        "TRUE",
        "FALSE",
        "LENGTH",
        "PRINT",
        # Literals
        "ID",
        "INT_LITERAL",
        "CHAR_LITERAL",
        "STRING_LITERAL",
        "boolean_literal",
        # Operators
        "EQ",
        "NE",
        "LE",
        "GE",
        "AND",
        "OR",
        "ASSIGN",
        "LT",
        "GT",
        "PLUS",
        "MINUS",
        "TIMES",
        "DIVIDE",
        "MOD",
        "NOT",
        # Punctuation
        "DOT",
        "SEMICOLON",
        "COMMA",
        "LPAREN",
        "RPAREN",
        "LBRACK",
        "RBRACK",
        "LBRACE",
        "RBRACE",
    }

    # ----------------------------------------------------------------
    # Identifiers and reserved words
    # ----------------------------------------------------------------
    # A dictionary mapping reserved words to token types.
    keywords = {
        "class": "CLASS",
        "extends": "EXTENDS",
        "public": "PUBLIC",
        "static": "STATIC",
        "void": "VOID",
        "main": "MAIN",
        "String": "STRING",
        "boolean": "BOOLEAN",
        "char": "CHAR",
        "int": "INT",
        "if": "IF",
        "else": "ELSE",
        "while": "WHILE",
        "for": "FOR",
        "assert": "ASSERT",
        "break": "BREAK",
        "return": "RETURN",
        "new": "NEW",
        "this": "THIS",
        "true": "TRUE",
        "false": "FALSE",
        "length": "LENGTH",
        "print" : "PRINT",
    }

    # ----------------------------------------------------------------
    # Rules
    # ----------------------------------------------------------------

    # String containing ignored characters (spaces and tabs)
    ignore = " \t"

    # Newlines
    @_(r"[\n]")
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    # Comments
    #@_(r"//.*|/\*.*\*/")
    @_(r"//.*|/\*[^*]*\*+(?:[^/*][^*]*\*+)*/")
    def ignore_comment(self, t):
        self.lineno += t.value.count("\n")

    # Identifiers
    @_(r"[a-zA-Z_][a-zA-Z0-9_]*")
    def ID(self, t):
        # Check if the identifier is a reserved word.
        t.type = self.keywords.get(t.value, "ID")
        return t
    
    # INT_LITERALS
    @_(r"[0-9]+")
    def INT_LITERAL(self, t):
        t.value = int(t.value)
        return t
    
    # CHAR_LITERALS
    @_(r"'(\\'|\\n|\\t|[^\\'])'")
    def CHAR_LITERAL(self, t):
        return t
    
    #@_(r"'(\\'|\\n|\\t|[^\\'])'")
    #def CHAR_LITERAL(self, t):
    #    t.value = t.value[1:-1]  # Remove as aspas
    #    return t


    # STRING_LITERALS
    #@_(r'"(\.|[^"])*"')
    @_(r'"([^"\\\n\r]|\\.)*"')
    def STRING_LITERAL(self, t):
        return t
    
    #BOOLEAN_LITERALS
    @_(r'(true|false)')
    def BOOLEAN_LITERAL(self, t):
        return t


    # ----------------------------------------------------------------
    # Operators and punctuation (order matters: longer tokens first)
    # ----------------------------------------------------------------
    EQ = r"=="
    NE = r"!="
    LE = r"<="
    GE = r">="
    AND = r"&&"
    OR = r"\|\|"
    ASSIGN = r"="
    LT = r"<"
    GT = r">"
    PLUS = r"\+"   # Regex special characters must be escaped
    MINUS = r"-"
    TIMES = r"\*"
    DIVIDE = r"/"
    MOD = r"%"
    NOT = r"!"

    DOT = r"\."
    SEMICOLON = r";"
    COMMA = r","
    LPAREN = r"\("
    RPAREN = r"\)"
    LBRACK = r"\["
    RBRACK = r"\]"
    LBRACE = r"\{"
    RBRACE = r"\}"


    
    # Continue the Lexer Rules
    


def main():
    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Path to file to be scanned", type=str)
    args = parser.parse_args()

    # get input path
    input_file = args.input_file
    input_path = pathlib.Path(input_file)

    # check if file exists
    if not input_path.exists():
        print("Input", input_path, "not found", file=sys.stderr)
        sys.exit(1)

    def print_error(msg, x, y):
        # use stdout to match with the output in the .out test files
        print(f"Lexical error: {msg} at {x}:{y}", file=sys.stdout)

    # Create the lexer and set error function
    lexer = MJLexer(print_error)

    # open file and print tokens
    with open(input_path) as f:
        lexer.scan(f.read())


if __name__ == "__main__":
    main()
