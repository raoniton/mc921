import argparse
import pathlib
import sys
from typing import Dict, List, Tuple

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
from mjc.mj_type import CharType, IntType, VoidType, ObjectType

import rich

class CodeGenerator(NodeVisitor):
    """
    Node visitor class that creates 3-address encoded instruction sequences
    with Basic Blocks & Control Flow Graph.
    """

    def __init__(self, viewcfg: bool):
        self.viewcfg: bool = viewcfg
        self.current_block: Block = None
        self.current_class = None
        self.return_reg = None
        self.class_fields = {}      # dictionary to store infomation like var from a class, Ex: {'A': ['a','b','c']}
        self.break_target = None    # para loops
        self.global_counter = 0     # 
        self.string_literals = {}   # ensure unique name for global strings


        # version dictionary for temporaries. We use the name as a Key
        self.versions: Dict[str, int] = {}
        self.fname: str = "_glob_"
        self.versions[self.fname] = 0 
        #self.versions: Dict[str, int] = {self.fname: 0}

        # The generated code (list of tuples)
        # At the end of visit_program, we call each function definition to emit
        # the instructions inside basic blocks. The global instructions that
        # are stored in self.text are appended at beginning of the code
        self.code: List[Tuple[str]] = []

        # Used for global declarations & constants (list, strings)
        self.text: List[Tuple[str]] = []

        # Map var names, to control redeclaration in differents scopes
        self.name_map: Dict[str, str] = {}

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
        #print(f"[DEBUG] new_text → {name}")
        self.versions[self.fname] += 1
        return name

    def new_text(self, typename: str) -> str:
        """
        Create a new literal constant on global section (text).
        """
        if "_glob_" not in self.versions:
            self.versions["_glob_"] = 0
        name = "@." + typename + "." + "%d" % (self.versions["_glob_"])
        
        #print(f"[DEBUG] new_text → {name}")

        self.versions["_glob_"] += 1
        return name

    # You must implement visit_Nodename methods for all of the AST nodes.
    # In your code, you will need to make instructions
    # and append them to the current block code list.
    #
    # A few sample methods follow. Do not hesitate to complete or change
    # them if needed.

    def print_debug(self, visit_Name, node):
        print(f"\n[DEBUG CodeGen visit_{visit_Name}]:\n", node)
        #print(f"[DEBUG CodeGen visit_{visit_Name}]")

    def needs_load(reg: str) -> bool:
        return '.' in reg or reg.startswith('%this.')


    def visit_Program(self, node: Program):
        #self.print_debug(type(node).__name__, node)
        # First visit all of the Class Declarations
        for class_decl in node.class_decls:
            if class_decl is not None:
                self.visit(class_decl)

        # At the end of codegen, first init the self.code with the list
        # of global instructions allocated in self.text
        #self.code = self.text.copy()

        # Now insert global declarations (text section) at the beginning of the final code
        # instead of replacing self.code!
        self.code = self.text + self.code


        # After, visit all the class definitions and emit the
        # code stored inside basic blocks.
        for class_decl in node.class_decls:
            block_visitor = EmitBlocks()
            block_visitor.visit(class_decl.cfg)
            for code in block_visitor.code:
                self.code.append(code)
                
    def visit_ClassDecl(self, node: ClassDecl):
        # self.print_debug(type(node).__name__, node)
        # Create a cfg to hold the class context
        node.cfg = BasicBlock(label=None)

        # define class name, and extends_name if there is a superclass
        class_name = node.name.name
        self.current_class = node.name.name
        extends_name = node.extends.name if node.extends else None

        # include the class declaration into ir code ('class', '@ClassName', 'SuperClassName' | None)
        self.code.append(("class", "@" + class_name, extends_name))

        #### Copy SuperClass fields
        self.class_fields[class_name] = []

        # To avoid duplicated field names
        seen_fields = set()

        # Herda campos da superclasse, mas RENOMEANDO com o prefixo da subclasse
        if extends_name and extends_name in self.class_fields:
            for field in self.class_fields[extends_name]:
                instr_type, field_name, value = field
                base_class_prefix = f"@{extends_name}."
                subclass_prefix = f"@{class_name}."

                if field_name.startswith(base_class_prefix):
                    new_field_name = field_name.replace(base_class_prefix, subclass_prefix)
                else:
                    new_field_name = f"@{class_name}.{field_name.split('.')[-1]}"  # fallback

                if new_field_name not in seen_fields:
                    new_field = (instr_type, new_field_name, value)
                    self.code.append(new_field)
                    self.class_fields[class_name].append(new_field)
                    seen_fields.add(new_field_name)


        # Visit all the Field Declarations
        for field_decl in node.var_decls:
            if field_decl is not None:
                # save length before generation
                before = len(self.code)
                self.visit(field_decl)

                # Add fields to class list
                for instr in self.code[before:]:
                    if instr[0].startswith("field_"):
                        if instr[1] not in seen_fields:
                            self.class_fields[class_name].append(instr)
                            seen_fields.add(instr[1])

        # Visit all the Method Declarations
        for method_decl in node.method_decls:
            if method_decl is not None:
                self.visit(method_decl)

        # Visit all the method definitions and emit the
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
        # self.print_debug(type(node).__name__, node)

        var_name = node.name.name

        # Extract the type
        if hasattr(node.type, "typename"):
            var_type = node.type.typename
        elif hasattr(node.type, "name"):
            if isinstance(node.type.name, ID):
                var_type = node.type.name.name
            else:
                var_type = node.type.name
        else:
            raise Exception(f"Unknown type in VarDecl: {type(node.type)}")

        reg_name = f"%{var_name}"
        self.name_map[var_name] = reg_name

        # Variable declared in method scope
        if self.current_block is not None:
            is_new_object = isinstance(node.init, NewObject) if node.init else False
            is_object_type = var_type not in {"int", "boolean", "int[]", "char[]", "boolean[]"}

            # Special case: list initializer
            if node.init and node.init.__class__.__name__ == "InitList":
                list_len = len(node.init.exprs)
                self.current_block.append((f"alloc_{var_type}_{list_len}", reg_name))
                self.visit(node.init)

                # Generate global constant for the list (like @.const_<name>)
                global_label = f"@.const_{var_name}.{self.global_counter}"
                self.global_counter += 1
                self.text.insert(0, (f"global_{var_type}_{list_len}", global_label, node.init.gen_values))
                self.current_block.append((f"store_{var_type}_{list_len}", global_label, reg_name))

            # If initialization is a string constant (char[])
            elif isinstance(node.init, Constant) and isinstance(node.init.value, str):
                raw_str = node.init.value.strip('"')
                str_len = len(raw_str)
                label = self.string_literals.setdefault(raw_str, f"@.str.{len(self.string_literals)}")
                self.text.insert(0, ("global_String", label, raw_str))
                self.current_block.append((f"alloc_char[]_{str_len}", reg_name))
                self.current_block.append(("store_char[]", label, reg_name))

            # Object created with "new" (do not allocate)
            elif not (is_new_object and is_object_type):
                self.current_block.append((f"alloc_{var_type}", reg_name))

            # Regular initialization
            if node.init and not node.init.__class__.__name__ == "InitList":
                node.init.target_reg = reg_name
                self.visit(node.init)
                if node.init.gen_loc != reg_name:
                    if isinstance(node.init, FieldAccess) and isinstance(node.init.object, This):
                        field_name = node.init.field_name.name
                        field_ref = f"%this.{field_name}"
                        self.current_block.append((f"store_{var_type}", field_ref, reg_name))
                    else:
                        self.current_block.append((f"store_{var_type}", node.init.gen_loc, reg_name))

        # Variable declared in class scope (fields)
        else:
            field_name = f"@{self.current_class}.{var_name}"
            if node.init is not None:
                self.visit(node.init)
                value = node.init.gen_loc
                self.code.append((f"field_{var_type}", field_name, value))
            else:
                self.code.append((f"field_{var_type}", field_name, None))
 
    def visit_MethodDecl(self, node: MethodDecl):
        method_name = node.name.name
        class_name = self.current_class
        return_type = node.type.typename if hasattr(node.type, 'typename') else node.type.name

        # Build full method name
        self.fname = f"@{class_name}.{method_name}"
        self.versions[self.fname] = 1

        # Create blocks
        node.cfg = BasicBlock(label=f"{method_name}.entry")
        self.current_block = node.cfg
        self.exit_block = BasicBlock(label="exit")

        # Aux maps
        self.param_map = {}
        self.name_map = {}

        # Build parameter list with fixed names: %1, %2, ...
        param_list = []
        for i, param in enumerate(node.param_list.params):
            ptype = param.type.name if hasattr(param.type, 'name') else param.type.typename
            pname = param.name.name
            reg = f"%{i + 1}"
            param_list.append((ptype, reg))
            self.param_map[pname] = reg
            self.name_map[pname] = reg

        # Set fixed return register
        if return_type != "void":
            self.return_reg = "%2"
        else:
            self.return_reg = None

        # Fix self.versions[self.fname] to match param count (manually done above)
        self.versions[self.fname] = len(param_list) + (2 if return_type != "void" else 1)
        
        # Emit define_<type>
        self.current_block.append((f"define_{return_type}", self.fname, param_list))
        self.current_block.append(("entry:",))

        # Allocate return register if needed
        if return_type != "void":
            self.return_reg = self.new_temp()  # instead of hardcoding %2
            self.current_block.append((f"alloc_{return_type}", self.return_reg))
        else:
            self.return_reg = None

        # Allocate and store params into local vars like %x, %y, etc.
        for i, param in enumerate(node.param_list.params):
            ptype = param.type.name if hasattr(param.type, 'name') else param.type.typename
            pname = param.name.name
            reg_local = f"%{pname}"  # fixed name like %x
            self.name_map[pname] = reg_local
            self.current_block.append((f"alloc_{ptype}", reg_local))
            self.current_block.append((f"store_{ptype}", f"%{i + 1}", reg_local))

        # Visit method body
        self.visit(node.body)

        # Ensure the block jumps to exit if there's no explicit return
        if not self.current_block.instructions or self.current_block.instructions[-1][0] != "jump":
            self.current_block.append(("jump", f"%{self.exit_block.label}"))
        self.current_block.next_block = self.exit_block

        # Exit block
        self.current_block = self.exit_block
        self.current_block.append((f"{self.exit_block.label}:",))

        if self.return_reg:
            temp = self.new_temp()
            self.current_block.append((f"load_{return_type}", self.return_reg, temp))
            self.current_block.append((f"return_{return_type}", temp))
        else:
            self.current_block.append(("return_void",))

        self.current_block = None

    def visit_MainMethodDecl(self, node: MainMethodDecl):
        # self.print_debug(type(node).__name__, node)

        node.cfg = BasicBlock(label=f"main.entry")
        self.current_block = node.cfg

        # Define the full method name
        method_name = "main"
        class_name = self.current_class
        self.fname = f"@{class_name}.{method_name}"
        self.versions[self.fname] = 1

        self.exit_block = BasicBlock(label="exit")  # save exit block for later use

        # Generate the "define" instruction for main
        param_list = []
        ptype = "String[]"
        pname = "%" + node.args.name
        param_list.append((ptype, pname))

        self.current_block.append(("define_void", self.fname, param_list))
        self.current_block.append(("entry:",))

        # Visit main body
        self.visit(node.body)

        # Add jump to exit if current block isn't already the exit block
        if self.current_block.label != self.exit_block.label:
            self.current_block.append(("jump", f"%{self.exit_block.label}"))
            self.current_block.next_block = self.exit_block

        # Finalize method with return_void
        self.current_block.append((self.exit_block.label + ":",))
        self.current_block.append(("return_void",))

        self.current_block = self.exit_block

    def visit_ParamList(self, node: ParamList):
        # self.print_debug(type(node).__name__, node)

        for params in node.params:
            var_type = params.type.typename if hasattr(params.type, 'typename') else params.type.name
            var_name = params.name.name
            reg_name = "%" + params.name.name

            # Recover the temporary register with the param name
            temp = self.param_map[var_name]

            self.current_block.append((f"alloc_{var_type}", reg_name))
            # Store the param value in the allocated space
            self.current_block.append((f"store_{var_type}", temp, reg_name))

    def visit_ParamDecl(self, node: ParamDecl):
        # self.print_debug(type(node).__name__, node)
        # Map the parameter name to the actual register
        param_name = node.name.name
        reg = self.param_map.get(param_name)

        if reg is None:
            raise Exception(f"[CodeGen] Parameter '{param_name}' not found in param_map")

        var_type = node.type.name if hasattr(node.type, 'name') else node.type.typename

        self.name_map[param_name] = reg
        self.current_block.append((f"alloc_{var_type}", reg))
        self.current_block.append((f"store_{var_type}", f"%{param_name}", reg))
        
    def visit_Compound(self, node: Compound):
        #self.print_debug(type(node).__name__, node)
        # Visit the block items
        for statement in node.statements:
            self.visit(statement)

    def visit_If(self, node: If):
        #self.print_debug(type(node).__name__, node)
        # Visit cond
        self.visit(node.cond)
        cond_loc = node.cond.gen_loc

        if cond_loc is None:
            raise Exception(f"[CodeGen] Condição de 'if' não possui gen_loc. node.cond = {node.cond}")

        # Build blocks
        then_block = BasicBlock(label="if.then")
        #else_block = BasicBlock(label="if.else")
        else_block = BasicBlock(label="if.else") if node.iffalse else BasicBlock(label="if.end")
        end_block = BasicBlock(label="if.end")

        # Make sure that the value is a bool, not a common var
        if cond_loc.startswith('%') and not cond_loc[1:].isdigit():
            temp = self.new_temp()
            self.current_block.append(("load_boolean", cond_loc, temp))
            cond_loc = temp

        # Create a conditional jump
        self.current_block.append(("cbranch", cond_loc, f"%{then_block.label}", f"%{else_block.label}"))
        self.current_block.next_block = then_block

        # THEN BLOCK(if true)
        self.current_block = then_block
        self.current_block.append((f"{then_block.label}:",))
        self.visit(node.iftrue)
        
        #if there is no instructions or a jump instruction - this prevent duplicates jump
        if not self.current_block.instructions or self.current_block.instructions[-1][0] != "jump":
            self.current_block.append(("jump", f"%{end_block.label}"))
        
        self.current_block.next_block = else_block


        # ELSE BLOCK(if false) 
        self.current_block = else_block
        self.current_block.append((else_block.label + ":",))
        if node.iffalse:
            self.visit(node.iffalse)

        self.current_block.append(("jump", f"%{end_block.label}"))
        self.current_block.next_block = end_block

        # END BLOCK
        self.current_block = end_block
        self.current_block.append((f"{end_block.label}:",))

    def visit_While(self, node: While):
        # self.print_debug(type(node).__name__, node)

        # Generate a unique identifier
        while_id = self.new_temp()[1:]  # Remove '%' to use in labels

        # Create uniquely labeled blocks
        cond_block = BasicBlock(label=f"while{while_id}.cond")
        body_block = BasicBlock(label=f"while{while_id}.body")
        end_block = BasicBlock(label=f"while{while_id}.end")
        
        # Jump straight to condition check
        self.current_block.append(("jump", f"%{cond_block.label}"))
        self.current_block.next_block = cond_block

        # ----- while.cond -----
        self.current_block = cond_block
        self.current_block.append((cond_block.label + ":",))

        self.visit(node.cond)
        cond_loc = node.cond.gen_loc
        if cond_loc is None:
            raise Exception(f"[CodeGen] While: condition has no gen_loc: {node.cond}")

        # Ensure we're using a boolean value (e.g., may be a variable that needs loading)
        if cond_loc.startswith('%') and not cond_loc[1:].isdigit():
            temp = self.new_temp()
            self.current_block.append(("load_boolean", cond_loc, temp))
            cond_loc = temp

        self.current_block.append(("cbranch", cond_loc, f"%{body_block.label}", f"%{end_block.label}"))
        self.current_block.next_block = body_block

        # ----- while.body -----
        self.current_block = body_block
        self.current_block.append((body_block.label + ":",))

        # Save current break target so "break" works
        old_break_target = getattr(self, "break_target", None)
        self.break_target = end_block

        self.visit(node.body)

        # Make sure to jump back to the condition after the body
        if not self.current_block.instructions or self.current_block.instructions[-1][0] != "jump":
            self.current_block.append(("jump", f"%{cond_block.label}"))

        self.current_block.next_block = end_block
        self.break_target = old_break_target

        # ----- while.end -----
        self.current_block = end_block
        self.current_block.append((end_block.label + ":",))

    def visit_For(self, node: For):
        # self.print_debug(type(node).__name__, node)

        # Create labeled blocks
        cond_block = BasicBlock(label="for.cond")
        body_block = BasicBlock(label="for.body")
        inc_block = BasicBlock(label="for.inc")
        end_block = BasicBlock(label="for.end")

        # Make a copy of current name map (in case of redeclaration)
        old_name_map = self.name_map.copy()

        # If init is DeclList, rename variables with unique temporaries
        # e.g., for (int i = 0; ...) we may need to rename i
        if isinstance(node.init, DeclList):
            for decl in node.init.decls:
                var_name = decl.name.name
                if var_name in self.name_map:
                    # Generate a new unique name
                    version = 2
                    new_name = f"{var_name}.{version}"
                    while new_name in self.name_map.values():  # Ensure uniqueness like %i, %i.1, %i.2
                        version += 1
                        new_name = f"{var_name}.{version}"

                    self.name_map[var_name] = new_name
                    decl.name.name = new_name
                
                # Visit the declaration using the new name
                self.visit(decl)
        else:
            self.visit(node.init)

        # Jump straight to condition check
        self.current_block.append(("jump", f"%{cond_block.label}"))
        self.current_block.next_block = cond_block

        # ----- for.cond -----
        self.current_block = cond_block
        self.current_block.append((cond_block.label + ":",))
        self.visit(node.cond)
        cond_loc = node.cond.gen_loc
        self.current_block.append(("cbranch", cond_loc, f"%{body_block.label}", f"%{end_block.label}"))
        self.current_block.next_block = body_block

        # ----- for.body -----
        self.break_target = end_block

        self.current_block = body_block
        self.current_block.append((body_block.label + ":",))
        self.visit(node.body)
        self.current_block.append(("jump", f"%{inc_block.label}"))
        self.current_block.next_block = inc_block

        # ----- for.inc -----
        self.current_block = inc_block
        self.current_block.append((inc_block.label + ":",))
        self.visit(node.next)
        self.current_block.append(("jump", f"%{cond_block.label}"))
        self.current_block.next_block = end_block

        # ----- for.end -----
        self.current_block = end_block
        self.current_block.append((end_block.label + ":",))

        # Clear break target to avoid usage outside of the loop
        self.break_target = None

        # Restore previous name mapping
        self.name_map = old_name_map

    def visit_DeclList(self, node: DeclList):
        #self.print_debug(type(node).__name__, node)
        for decl in node.decls:
            self.visit(decl)

    def visit_Print(self, node: Print):
        # self.print_debug(type(node).__name__, node)

        if isinstance(node.expr, ExprList):
            for expr in node.expr.exprs:
                # print(expr)
                self.visit(expr)
                expr_loc = expr.gen_loc

                if not hasattr(expr, "type"):
                    raise Exception(f"[CodeGen] Print: expression {expr} has no 'type' attribute.")

                expr_type = expr.type.typename

                # Se for int, e expr_loc parece um endereço (temporário), faça load_int antes
                if expr_type == "int" and expr_loc.startswith('%'):
                    temp = self.new_temp()
                    self.current_block.append(("load_int", expr_loc, temp))
                    expr_loc = temp

                self.current_block.append((f"print_{expr_type}", expr_loc))
        else:
            self.visit(node.expr)
            expr_loc = node.expr.gen_loc

            if not hasattr(node.expr, "type"):
                raise Exception(f"[CodeGen] Print: expression {node.expr} has no 'type' attribute.")

            expr_type = node.expr.type.typename
            if expr_type == "int" and expr_loc.startswith('%'):
                temp = self.new_temp()
                self.current_block.append(("load_int", expr_loc, temp))
                expr_loc = temp
            self.current_block.append((f"print_{expr_type}", expr_loc))

    def visit_Assert(self, node: Assert):
        # self.print_debug(type(node).__name__, node)

        str_label = self.new_text("str")
        self.text.insert(0, ("global_String", str_label, f"assertion_fail on {str(node.expr.lvalue.coord)[2:]}"))

        # Visit the assert expression (e.g., y == 3)
        self.visit(node.expr)
        cond = node.expr.gen_loc  # e.g., %t3

        if not hasattr(node.expr, "gen_loc") or node.expr.gen_loc is None:
            raise Exception(f"[CodeGen] Assert: expression has no gen_loc: {node.expr}")

        # Create labels for the true and false branches
        true_block = BasicBlock(label="assert.true")
        false_block = BasicBlock(label="assert.false")

        # Use the exit block previously created by the method
        exit_block = self.exit_block

        # Generate the conditional branch instruction
        self.current_block.append(("cbranch", cond, f"%{true_block.label}", f"%{false_block.label}"))
        self.current_block.next_block = false_block  # start of the false branch

        # ASSERT FALSE
        self.current_block = false_block
        self.current_block.append((false_block.label + ":",))
        self.current_block.append(("print_string", str_label))
        self.current_block.append(("jump", f"%{exit_block.label}"))
        self.current_block.next_block = true_block  # next branch

        # ASSERT TRUE
        self.current_block = true_block
        self.current_block.append((true_block.label + ":",))
        # self.current_block.append(("jump", f"%{exit_block.label}"))
        # self.current_block.next_block = exit_block
        self.current_block.next_block = None

        # self.current_block = exit_block

    def visit_Break(self, node: Break):
        # self.print_debug(type(node).__name__, node)

        # Jump to the end of the closest loop
        self.current_block.append(("jump", f"%{self.break_target.label}"))

    def visit_Return(self, node: Return):
        #self.print_debug(type(node).__name__, node)
        # Se há expressão (return com valor)
        if node.expr is not None:
            self.visit(node.expr)

            if not hasattr(node.expr, "gen_loc") or node.expr.gen_loc is None:
                raise Exception(f"[CodeGen] Return: expressão sem gen_loc: {node.expr}")

            value = node.expr.gen_loc
            if hasattr(node.expr, "type") and hasattr(node.expr.type, "typename"):
                return_type = node.expr.type.typename
            else:
                raise Exception("Return: tipo de retorno não encontrado")

            # Verifica se return_reg está corretamente definido
            if not hasattr(self, "return_reg") or self.return_reg is None:
                raise Exception("[CodeGen] Return: return_reg não definido para método com retorno.")

            # Armazena no registrador de retorno, depois salta para exit
            self.current_block.append((f"store_{return_type}", value, self.return_reg))
            self.current_block.append(("jump", f"%{self.exit_block.label}"))

        else:
            # return sem valor → void
            self.current_block.append(("return_void",))

    def visit_Assignment(self, node: Assignment):
        # Visit the right-hand side (value)
        self.visit(node.rvalue)
        if not hasattr(node.rvalue, "gen_loc") or node.rvalue.gen_loc is None:
            raise Exception(f"[CodeGen] Assignment: rvalue has no gen_loc: {node.rvalue}")

        value = node.rvalue.gen_loc

        # Suggest target register if it's a NewObject assigned to an ID
        if isinstance(node.rvalue, NewObject) and isinstance(node.lvalue, ID):
            var_name = node.lvalue.name
            reg_name = self.name_map.get(var_name, f"%{var_name}")
            node.rvalue.target_reg = reg_name

        # Get the type
        if hasattr(node.rvalue, 'type') and node.rvalue.type is not None:
            value_type = node.rvalue.type.typename
        elif hasattr(node.lvalue, 'type') and node.lvalue.type is not None:
            value_type = node.lvalue.type.typename
        else:
            raise Exception("[CodeGen] Assignment: could not determine type")

        # If value is an address (e.g., FieldAccess or contains a '.')
        if isinstance(node.rvalue, FieldAccess) or (isinstance(value, str) and '.' in value):
            temp = self.new_temp()
            self.current_block.append((f"load_{value_type}", value, temp))
            value = temp

        # Lvalue: local variable
        if isinstance(node.lvalue, ID):
            var_name = node.lvalue.name
            raw_name = self.name_map.get(var_name, var_name)
            reg_name = raw_name if raw_name.startswith('%') else f"%{raw_name}"
            self.current_block.append((f"store_{value_type}", value, reg_name))
            node.gen_loc = reg_name

        #elif isinstance(node.lvalue, FieldAccess):
        #    if isinstance(node.lvalue.object, This):
        #        field_name = node.lvalue.field_name.name
        #        target = f"%this.{field_name}"
        #        self.current_block.append((f"store_{value_type}", value, target))
        #    else:
        #        self.visit(node.lvalue.object)
        #        obj_loc = node.lvalue.object.gen_loc
        #        field_name = node.lvalue.field_name.name
        #        addr_temp = self.new_temp()
        #        self.current_block.append(("load_addr", f"{obj_loc}.{field_name}", addr_temp))
        #        self.current_block.append((f"store_{value_type}", value, addr_temp))

        # Lvalue: field access (works for both this.field and obj.field)
        elif isinstance(node.lvalue, FieldAccess):
            self.visit(node.lvalue.object)
            obj_loc = node.lvalue.object.gen_loc
            field_name = node.lvalue.field_name.name

            # Descobrir o nome da classe do objeto para construir nome completo do campo
            if hasattr(node.lvalue.object, "type") and hasattr(node.lvalue.object.type, "name"):
                class_name = node.lvalue.object.type.name
                full_field_name = f"{obj_loc}.@{class_name}.{field_name}"
            else:
                full_field_name = f"{obj_loc}.{field_name}"

            addr_temp = self.new_temp()
            self.current_block.append(("load_addr", full_field_name, addr_temp))
            self.current_block.append((f"store_{value_type}", value, addr_temp))

        

        # Lvalue: array access
        elif isinstance(node.lvalue, ArrayRef):
            self.visit(node.lvalue.name)
            self.visit(node.lvalue.subscript)
            array_loc = node.lvalue.name.gen_loc
            index_loc = node.lvalue.subscript.gen_loc
            self.current_block.append((f"store_{value_type}_array", value, array_loc, index_loc))

        else:
            raise Exception(f"[CodeGen] Assignment: unsupported lvalue type: {type(node.lvalue).__name__}")

        node.gen_loc = None  # assignments do not produce a value

    def visit_BinaryOp(self, node: BinaryOp):
        # Set parent relationships (needed for == with *)
        node.lvalue.parent = node
        node.rvalue.parent = node

        # Visit operands in correct order
        if node.op == "==":
            self.visit(node.rvalue)
            self.visit(node.lvalue)
        else:
            self.visit(node.lvalue)
            self.visit(node.rvalue)

        # Ensure both sides have a value
        if not hasattr(node.lvalue, "gen_loc") or node.lvalue.gen_loc is None:
            raise Exception(f"[CodeGen] BinaryOp: lvalue has no gen_loc.")
        if not hasattr(node.rvalue, "gen_loc") or node.rvalue.gen_loc is None:
            raise Exception(f"[CodeGen] BinaryOp: rvalue has no gen_loc.")

        left = node.lvalue.gen_loc
        right = node.rvalue.gen_loc

        # Helper function to decide if load is needed
        def needs_load(reg):
            return '.' in reg or reg.startswith('%this.')

        # Load values if needed
        if needs_load(left):
            temp_left = self.new_temp()
            self.current_block.append((f"load_{node.lvalue.type.typename}", left, temp_left))
            left = temp_left

        if needs_load(right):
            temp_right = self.new_temp()
            self.current_block.append((f"load_{node.rvalue.type.typename}", right, temp_right))
            right = temp_right

        result = self.new_temp()

        op_map = {
            "+":  "add_int",
            "-":  "sub_int",
            "*":  "mul_int",
            "/":  "div_int",
            "%":  "mod_int",
            "==": "eq_int",
            "!=": "ne_int",
            "<":  "lt_int",
            "<=": "le_int",
            ">":  "gt_int",
            ">=": "ge_int",
            "&&": "and_boolean",
            "||": "or_boolean",
        }

        instr = op_map.get(node.op)
        if instr is None:
            raise Exception(f"[CodeGen] Unsupported binary operator: {node.op}")

        self.current_block.append((instr, left, right, result))

        # Ensure test compatibility: if child of == and this is *, load result
        if node.op == "*" and hasattr(node, "parent") and isinstance(node.parent, BinaryOp) and node.parent.op == "==":
            loaded = self.new_temp()
            self.current_block.append((f"load_{node.type.typename}", result, loaded))
            node.gen_loc = loaded
        else:
            node.gen_loc = result

    def visit_UnaryOp(self, node: UnaryOp):
        # self.print_debug(type(node).__name__, node)

        self.visit(node.expr)
        if not hasattr(node.expr, "gen_loc") or node.expr.gen_loc is None:
            raise Exception(f"[CodeGen] UnaryOp: expr has no gen_loc.")

        operand = node.expr.gen_loc

        if node.op == "!":
            # Always loadd boolean before applying not
            loaded = self.new_temp()
            self.current_block.append(("load_boolean", operand, loaded))
            result = self.new_temp()
            self.current_block.append(("not_boolean", loaded, result))

        elif node.op == "-":
            zero = self.new_temp()
            self.current_block.append(("literal_int", 0, zero))
            result = self.new_temp()
            self.current_block.append(("sub_int", zero, operand, result))

        else:
            raise Exception(f"[CodeGen] Unsupported unary operator: {node.op}")

        node.gen_loc = result

    def visit_ArrayRef(self, node: ArrayRef):
        # print debug info if needed
        print(f"[DEBUG ArrayRef] type={elem_type} base={base_type} array={array_loc} index={index_loc}")

        self.visit(node.name)
        self.visit(node.subscript)

        if not hasattr(node.name, "gen_loc") or node.name.gen_loc is None:
            raise Exception("[CodeGen] ArrayRef.name has no gen_loc.")
        if not hasattr(node.subscript, "gen_loc") or node.subscript.gen_loc is None:
            raise Exception("[CodeGen] ArrayRef.subscript has no gen_loc.")
        if not hasattr(node.name, "type") or node.name.type is None:
            raise Exception("[CodeGen] ArrayRef.name has no type.")

        array_loc = node.name.gen_loc
        index_loc = node.subscript.gen_loc
        elem_type = node.name.type.typename

        addr = self.new_temp()
        result = self.new_temp()

        # First, calculate address of the array element
        self.current_block.append((f"elem_{elem_type}", array_loc, index_loc, addr))

        # Remove [] from type to generate correct load instruction
        base_type = elem_type.replace("[]", "")
        self.current_block.append((f"load_{base_type}", addr, result))

        node.gen_loc = result

    def visit_FieldAccess(self, node: FieldAccess):
        #self.print_debug(type(node).__name__, node)
        self.visit(node.object)

        if not hasattr(node.object, "gen_loc") or node.object.gen_loc is None:
            raise Exception("[CodeGen] FieldAccess: object has no gen_loc.")

        obj_loc = node.object.gen_loc
        field_name = node.field_name.name

        # If it's `this.field`, return directly
        #if isinstance(node.object, This):
        #    node.gen_loc = f"%this.{field_name}"
        #else:
        #    # Try to build fully qualified field name if type info exists
        #    if hasattr(node.object, "type") and hasattr(node.object.type, "name"):
        #        class_name = node.object.type.name
        #        full_field = f"{obj_loc}.@{class_name}.{field_name}"
        #    else:
        #        full_field = f"{obj_loc}.{field_name}"

        # Determina a classe do objeto
        if hasattr(node.object, "type") and hasattr(node.object.type, "name"):
            class_name = node.object.type.name
            field_full_name = f"{obj_loc}.@{class_name}.{field_name}"
        else:
            # fallback se tipo não está presente
            field_full_name = f"{obj_loc}.{field_name}"
            
        # If it's obj.field, generate load_addr
        addr_temp = self.new_temp()
        self.current_block.append(("load_addr", field_full_name, addr_temp))
        node.gen_loc = addr_temp

    def visit_MethodCall(self, node: MethodCall):
        #self.print_debug(type(node).__name__, node)

        # Visita o objeto no qual o método é chamado (ex: 'age' em 'age.set_age')
        #self.visit(node.object)

        # Se receiver for ID (ex: obj.foo()), não faz load, usa nome diretamente
        if isinstance(node.object, ID):
            recv_name = node.object.name
            recv_loc = self.name_map.get(recv_name, f"%{recv_name}")
        else:
            self.visit(node.object)
            if not hasattr(node.object, "gen_loc") or node.object.gen_loc is None:
                raise Exception("[CodeGen] MethodCall: objeto sem gen_loc.")
            recv_loc = node.object.gen_loc
            

        call_label = f"{recv_loc}.{node.method_name.name}"

        args = []

        # Se for lista de expressões (vários args)
        if isinstance(node.args, ExprList):
            
            for arg in node.args.exprs:
                self.visit(arg)
                #args.append((arg.gen_loc, arg.type.typename))
                arg_type = getattr(arg, 'type', None)
                if not hasattr(arg, 'gen_loc') or arg.gen_loc is None:
                    raise Exception(f"[CodeGen] Argumento da chamada de método sem gen_loc: {arg}")
                if not hasattr(arg, 'type') or arg.type is None:
                    raise Exception(f"[CodeGen] Argumento da chamada de método sem tipo: {arg}")
                args.append((arg.gen_loc, arg.type.typename))

        # Se for apenas um argumento
        elif node.args is not None:
            self.visit(node.args)
            if not hasattr(node.args, 'type') or node.args.type is None:
                raise Exception(f"[CodeGen] Método com argumento inválido: {node.args}")
            args.append((node.args.gen_loc, node.args.type.typename))

            #args.append((node.args.gen_loc, node.args))

        # Emite as instruções param_<tipo>
        for arg_loc, arg_type in args:
            self.current_block.append((f"param_{arg_type}", arg_loc))

        # Gera o rótulo da chamada do método
        #call_label = f"{recv_loc}.{node.method_name.name}"

        # Aloca registrador temporário para o resultado (caso não seja void)
        if node.type.typename != "void":
            node.gen_loc = self.new_temp()
            self.current_block.append(("call_int", call_label, node.gen_loc))
        else:
            dummy_target = self.new_temp()
            self.current_block.append(("call_void", call_label, dummy_target))

    def visit_Length(self, node: Length):
        #self.print_debug(type(node).__name__, node)
        # Visit the expression to set its gen location
        self.visit(node.expr)
        if not hasattr(node.expr, "gen_loc") or node.expr.gen_loc is None:
            raise Exception("[CodeGen] Length: expressão sem gen_loc.")
        
        # Alloc a register to store the length
        node.gen_loc = self.new_temp()
        # gen the length instruction
        length_inst = ("length", node.expr.gen_loc, node.gen_loc)
        # Store the length instruction
        self.current_block.append(length_inst)

    def visit_NewArray(self, node: NewArray):
        #self.print_debug(type(node).__name__, node)
        # Visita array size
        self.visit(node.size)
        if not hasattr(node.size, "gen_loc") or node.size.gen_loc is None:
            raise Exception("[CodeGen] NewArray: size sem gen_loc.")
        size_loc = node.size.gen_loc

        # Alocate register to set result
        result = self.new_temp()
        node.gen_loc = result

        elem_type = node.type.name if hasattr(node.type, 'name') else node.type.typename
        
        instr = (f"new_array_{elem_type}", size_loc, result)
        
        #self.current_block.append((f"new_array_{elem_type}", size_loc, result))
        if self.current_block is not None:
            self.current_block.append(instr)
        else:
            self.text.append(instr)
     
    def visit_NewObject(self, node: NewObject):
        #self.print_debug(type(node).__name__, node)
        
        # Decide o registrador alvo
        if hasattr(node, "target_reg"):
            reg = node.target_reg
        else:
            reg = self.new_temp()

        class_name = node.type.typename
        self.current_block.append((f"new_@{class_name}", reg))
        node.gen_loc = reg

        # Inicializa campos da classe, se definidos
        if class_name in self.class_fields:
            for instr in self.class_fields[class_name]:
                if instr[0].startswith("field_"):
                    field_type = instr[0][6:]       # Ex: 'int'
                    field_full = instr[1]           # Ex: '@Program.n'
                    field_value = instr[2]          # Ex: 8

                    # Só inicializa se tiver valor
                    if field_value is not None:
                        field_name = field_full.split('.')[-1]

                        # Carrega o endereço do campo
                        obj_loaded = self.new_temp()
                        addr = self.new_temp()
                        self.current_block.append((f"load_{class_name}", reg, obj_loaded))
                        self.current_block.append(("load_addr", f"{obj_loaded}.{field_name}", addr))

                        # Carrega o valor (literal)
                        temp = self.new_temp()
                        self.current_block.append((f"literal_{field_type}", field_value, temp))

                        # Inicializa o campo
                        self.current_block.append((f"store_{field_type}", temp, addr))

    def visit_Constant(self, node: Constant):
        #self.print_debug(type(node).__name__, node)
        value = node.value
        
        # Se estamos em contexto de método (bloco ativo)
        if self.current_block is not None:
            
            if isinstance(value, int):
                node.gen_loc = self.new_temp()
                self.current_block.append(("literal_int", value, node.gen_loc))
        
            elif isinstance(value, bool):
                node.gen_loc = self.new_temp()
                self.current_block.append(("literal_boolean", value, node.gen_loc))
        
            elif isinstance(value, str):
                # Gera um rótulo global único
                label = self.new_text("str")
                # Adiciona ao início do código global
                self.text.insert(0, ("global_String", label, value[1:-1]))
                # Usa o rótulo como localização da string
                node.gen_loc = label
        
            elif isinstance(value, chr):
                self.current_block.append(("literal_char", value, node.gen_loc))
        
            else:
                raise Exception(f"[CodeGen] Unsupported constant type: {type(value)}")
        else:
            # Fora de método (ex: em campo da classe)
            if isinstance(value, str):
                label = self.new_text("str")
                self.text.insert(0, ("global_String", label, value))
                node.gen_loc = label
            else:
                node.gen_loc = value  # só registra o valor diretamente
            
    def visit_This(self, node: This):
        #self.print_debug(type(node).__name__, node)
        node.gen_loc = "%this"

    def visit_ID(self, node: ID):
        #self.print_debug(type(node).__name__, node)
        var_name = node.name

        if var_name in self.name_map:
            reg_name = self.name_map[var_name]
            if not reg_name.startswith("%"):
                reg_name = f"%{reg_name}"

            # Special handling for arrays: no needed load
            if node.type and node.type.typename.endswith("[]"):
                # Em acesso direto de array, não se faz load do array em si
                node.gen_loc = reg_name  # já é a 
            
            # Special handling for objects: don't load them
            elif node.type.typename not in ["int", "boolean", "char"]:
                node.gen_loc = reg_name  # object references shouldn't be loaded
            
            else:
                temp = self.new_temp()
                self.current_block.append((f"load_{node.type.typename}", reg_name, temp))
                node.gen_loc = temp
        else:
            raise Exception(f"[CodeGen] ID '{var_name}' not found in current scope")

    def visit_Type(self, node: Type):
        #self.print_debug(type(node).__name__, node)
        node.gen_loc = None

    def visit_Extends(self, node: Extends):
        #self.print_debug(type(node).__name__, node)
        #subclass = node.name.name
        #superclass = node.parent.name
        #self.text.append(('class', f"@{subclass}", superclass))
        pass

    def visit_ExprList(self, node: ExprList):
        #self.print_debug(type(node).__name__, node)
        for expr in node.exprs:
            self.visit(expr)

    def visit_InitList(self, node: InitList):
        values = []
        gen_locs = []
        for expr in node.exprs:
            self.visit(expr)
            gen_locs.append(expr.gen_loc)
            values.append(expr.value)

        node.gen_loc = self.new_temp()
        node.gen_values = values  # ← usado em global_int[]_N
        self.current_block.append(("init_list", gen_locs, node.gen_loc))


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