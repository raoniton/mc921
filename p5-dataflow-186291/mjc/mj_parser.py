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

    precedence = ()

    # ------------------------------------------------------------
    # Parser Rules
    # ------------------------------------------------------------

    @_("")
    def empty(self, p):
        pass

    @_("ID")
    def identifier(self, p):
        pass

    @_("class_declaration_list")
    def program(self, p):
        pass

    # Declarations of Classes

    @_("class_declaration", "class_declaration_list class_declaration")
    def class_declaration_list(self, p):
        pass

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
