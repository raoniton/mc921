from typing import List, Optional, Tuple

from graphviz import Digraph


def format_instruction(t: tuple) -> str:
    """Pretty prints instruction.

    ## Parameters
    - :param t: instruction

    ## Return
    - :return: The formatted instruction t'
    """
    operand = t[0].split("_")
    op = operand[0]
    ty = operand[1] if len(operand) > 1 else None
    if len(operand) >= 3:
        for _qual in operand[2:]:
            if _qual == "*":
                ty += "*"
            else:
                ty += f"[{_qual}]"
    if len(t) > 1:
        if op == "define":
            return (
                f"{op} {ty} {t[1]} ("
                + ", ".join(list(" ".join(el) for el in t[2]))
                + ")"
            )
        elif op == "class":
            extends = "" if t[2] is None else f" extends {t[2]}"
            return f"\n{op} {t[1]}{extends}"
        elif op == "field":
            init_value = "" if t[2] is None else f" init = {t[2]}"
            return f"{op} {ty} {t[1]}{init_value}"
        else:
            _str = "" if op == "global" else "  "
            if op == "jump":
                _str += f"{op} label {t[1]}"
            elif op == "cbranch":
                _str += f"{op} {t[1]} label {t[2]} label {t[3]}"
            elif op == "global":
                if ty.startswith("String"):
                    _str += f"{t[1]} = {op} {ty} '{t[2]}'"
                elif len(t) > 2:
                    _str += f"{t[1]} = {op} {ty} {t[2]}"
                else:
                    _str += f"{t[1]} = {op} {ty}"
            elif op == "return" or op == "print":
                _str += f"{op} {ty} {t[1]}"
            elif op == "sitofp" or op == "fptosi":
                _str += f"{t[2]} = {op} {t[1]}"
            elif op == "store" or op == "param":
                _str += f"{op} {ty} "
                for _el in t[1:]:
                    _str += f"{_el} "
            else:
                _str += f"{t[-1]} = {op} {ty} "
                for _el in t[1:-1]:
                    _str += f"{_el} "
            return _str
    elif ty == "void":
        return f"  {op}"
    else:
        return f"{op}"


class Block:
    def __init__(self, label: str):
        self.label: str = label  # Label that identifies the block
        self.instructions: List[Tuple[str]] = []  # Instructions in the block
        self.predecessors: List[Block] = []  # List of predecessors
        self.next_block: Optional[Block] = None  # Link to the next block

    def append(self, instr):
        self.instructions.append(instr)

    def __iter__(self):
        return iter(self.instructions)


class BasicBlock(Block):
    """
    Class for a simple basic block.  Control flow unconditionally
    flows to the next block.
    """

    def __init__(self, label: str):
        super(BasicBlock, self).__init__(label)
        self.branch: Optional[Block] = (
            None  # Not necessary the same as next_block in the linked list
        )


class ConditionBlock(Block):
    """
    Class for a block representing an conditional statement.
    There are two branches to handle each possibility.
    """

    def __init__(self, label: str):
        super(ConditionBlock, self).__init__(label)
        self.taken: Optional[Block] = None
        self.fall_through: Optional[Block] = None


class BlockVisitor(object):
    """
    Class for visiting blocks.  Define a subclass and define
    methods such as visit_BasicBlock or visit_ConditionalBlock to
    implement custom processing (similar to ASTs).
    """

    def visit(self, block: Block):
        while isinstance(block, Block):
            name = "visit_%s" % type(block).__name__
            if hasattr(self, name):
                getattr(self, name)(block)
            block = block.next_block


class EmitBlocks(BlockVisitor):
    def __init__(self):
        self.code: List[Tuple[str]] = []

    def visit_BasicBlock(self, block: Block):
        for inst in block.instructions:
            self.code.append(inst)

    def visit_ConditionBlock(self, block: Block):
        for inst in block.instructions:
            self.code.append(inst)


class CFG:
    def __init__(self, fname: str):
        self.fname: str = fname
        self.g = Digraph(
            "g", filename=fname.replace("@", "") + ".gv", node_attr={"shape": "record"}
        )

    def visit_BasicBlock(self, block: Block):
        # Get the label as node name
        _name = block.label
        if _name:
            # get the formatted instructions as node label
            _label = "{" + _name + ":\\l\t"
            for _inst in block.instructions[1:]:
                _label += format_instruction(_inst) + "\\l\t"
            _label += "}"
            self.g.node(_name, label=_label)
            if block.branch:
                self.g.edge(_name, block.branch.label)
        else:
            # Function definition. An empty block that connect to the Entry Block
            self.g.node(self.fname, label=None, _attributes={"shape": "ellipse"})
            self.g.edge(self.fname, block.next_block.label)

    def visit_ConditionBlock(self, block: Block):
        # Get the label as node name
        _name = block.label
        # get the formatted instructions as node label
        _label = "{" + _name + ":\\l\t"
        for _inst in block.instructions[1:]:
            _label += format_instruction(_inst) + "\\l\t"
        _label += "|{<f0>T|<f1>F}}"
        self.g.node(_name, label=_label)
        self.g.edge(_name + ":f0", block.taken.label)
        self.g.edge(_name + ":f1", block.fall_through.label)

    def view(self, block):
        while isinstance(block, Block):
            name = "visit_%s" % type(block).__name__
            if hasattr(self, name):
                getattr(self, name)(block)
            block = block.next_block
        # You can use the next stmt to see the dot file
        # print(self.g.source)
        self.g.view()
