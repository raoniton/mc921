from typing import Any, Dict, List, Tuple

# MJIR Instruction: (operation, operands, ..., destination)
Instruction = Tuple
Address = int
Value = Any

# Constants
MEMORY_SIZE = 10_000

PRIMITIVE_TYPES = ["int", "char", "boolean"]
ARRAY_TYPES = ["int[]", "char[]", "String"]


# Runtime Representations
class MJClassTemplate:
    def __init__(
        self,
        name: str,
        fields: Dict[str, Any],
        methods: Dict[str, Dict[str, Any]],
        parent=None,
    ):
        self.name = name
        self.parent = parent
        self.fields = fields
        self.methods = methods
        if self.parent is not None:
            self.fields.update(self.parent.fields)
            self.methods.update(self.parent.methods)


class MJClassInstance:
    def __init__(
        self, name: str, template: MJClassTemplate, field_locs: dict, method_locs: dict
    ):
        self.name = name
        self._template = template
        self._field_locs = field_locs
        self._method_locs = method_locs

    def get_field_data(self, field: str) -> dict:
        return self._field_locs[field]

    def get_field_loc(self, field: str) -> Address:
        return self._field_locs[field]["addr"]

    def get_field_type(self, field: str) -> str:
        return self._field_locs[field]["type"]

    def get_field_size(self, field: str) -> int:
        return self._field_locs[field]["size"]

    def get_method_loc(self, method: str) -> Address:
        return self._method_locs[method]

    def __str__(self):
        return f"{self.name}({self._template.name})"

    def __repr__(self):
        return self.__str__()


class Memory:
    def __init__(self):
        self._mem_size = MEMORY_SIZE
        self._memory = [None] * self._mem_size
        self._mp = 0  # Points to the first available memory cell
        self._mp_stack = []

    def reset_memory(self):
        self._mp = 0

    def push_mp(self):
        self._mp_stack.append(self._mp)

    def pop_mp(self):
        self._mp = self._mp_stack.pop()

    def mem_dump(self):
        return self._memory[: self._mp]

    def alloc(self, size: int = 1) -> Address:
        addr = self._mp
        self._mp += size
        return addr

    def store_value(self, addr: Address, value: Any):
        self._memory[addr] = value

    def store_array(self, addr: Address, size: int, array: List[Any]):
        self._memory[addr : addr + size] = array

    def load_value(self, addr: Address) -> Any:
        return self._memory[addr]

    def load_array(self, addr: Address, size: int) -> List[Any]:
        return self._memory[addr : addr + size]


class MJIRInterpreter:
    def __init__(self):
        self._code = []
        self._code_len = len(self._code)
        self._start = 0  # Entry Point
        self._pc = 0  # Program counter

        self._registers = {}  # Register Bank
        self._globals = {}  # Global names (heap allocated)
        self._labels = {}  # Labels (jump targets)
        self._reg_stack = []  # Stack of per method register bank
        self._method_params = []  # list of parameters when calling a method
        self._returns = []  # Stack of register names (in the caller) to return value
        self._pcstack = []  # Stack of return addresses (program counters)
        self._method_stack = []  # Save the names of the previous methods

        self._memory = Memory()

        self._class_templates = {}

    def _unpack_instruction(self, instruction: Instruction):
        operation, *args = instruction
        return operation, args

    def _extract_operation(self, raw_op: str):
        op, *modifiers = raw_op.split("_")
        return op, modifiers

    def _parse_to_type(self, value: Any, type: str):
        parser = {
            "int": lambda x: int(x),
            "char": lambda x: str(x),
        }
        if value is not None and type in parser.keys():
            return parser[type](value)
        return value

    def _build_class_templates(self):
        """This method walks through the program code
        to find class definitions and create
        class templates (MJClassTemplate)
        using those found class definitions.
        It assumes that class definitions precede
        field and method definitions of that class.
        """

        def _unpack_arg(field_raw):
            temp = field_raw.split(".")
            class_name = temp[0]
            field_name = temp[-1]
            return class_name, field_name

        code_walker = 0
        while True:
            if code_walker >= self._code_len:
                break
            curr_inst = self._code[code_walker]
            raw_op, args = self._unpack_instruction(curr_inst)
            operation, modifier = self._extract_operation(raw_op)

            if operation == "global":
                # Store the global variable in memory
                varname = args[0]
                self._alloc_global(varname)

                # Get the type and size of the global variable
                array_value = args[1]
                type_modifier = modifier[0]
                size = len(array_value)

                # Allocate memory for the global constant array
                saddr = self._memory.alloc(size=size)

                # Store the array in memory
                self._memory.store_array(saddr, size, array_value)

                # Create a struct with the base address and size
                # of the array
                array_struct = {"addr": saddr, "size": size, "type": type_modifier}
                # Store the array struct in memory
                self._store(varname, array_struct)

            elif operation == "class":
                class_name = args[0]
                parent = self._class_templates.get(args[1])
                self._class_templates[class_name] = MJClassTemplate(
                    name=class_name, fields={}, methods={}, parent=parent
                )

            elif operation == "field":
                class_name, field_name = _unpack_arg(args[0])
                self._class_templates[class_name].fields[field_name] = {
                    "value": self._parse_to_type(args[1], modifier[0]),
                    "type": modifier[0],
                }

            elif operation == "define":
                class_name, method_name = _unpack_arg(args[0])
                self._class_templates[class_name].methods[method_name] = {
                    "entrypoint": code_walker,
                    "params": args[1],
                }
                self._labels[method_name] = {}

                if method_name == "main":
                    self._start = code_walker

            elif len(curr_inst) == 1 and curr_inst[0] not in [
                "return_void",
                "print_void",
            ]:
                # This is a label inside a method
                # we need to store the address of the label
                # in the method label table
                label_name = curr_inst[0]
                self._labels[method_name][f"%{label_name[:-1]}"] = code_walker

            code_walker += 1

    def _next_instruction(self):
        next_instruction = self._code[self._pc]
        self._pc += 1
        return next_instruction

    #
    # Auxiliar functions to manage memory
    #

    def _is_field_access(self, varname: str):
        """Returns True if varname is a field_access (%var.field)"""
        return (
            "." in varname
            and varname.startswith("%")
            and not varname.split(".")[-1].isdigit()
        )

    def _get_object_and_field(self, varname: str) -> Tuple:
        obj, field = varname.split(".")
        return obj, field

    def _get_field_addr(self, varname: str) -> Address:
        obj_reg, field = self._get_object_and_field(varname)
        obj: MJClassInstance = self._load(obj_reg)
        field_addr = obj.get_field_loc(field)
        return field_addr

    def _get_field_data(self, varname: str) -> dict:
        obj_reg, field = self._get_object_and_field(varname)
        obj: MJClassInstance = self._load(obj_reg)
        return obj.get_field_data(field)

    def _push(self, arg_registers: List[str], no_return: bool = False):
        # Save the current state of the registers
        self._reg_stack.append(self._registers)
        # Save the state of the frame pointer
        self._memory.push_mp()

        # Clear the register bank
        self._registers = {}

        if no_return:
            self._alloc_reg("%0")
            self._store("%0", None)

        # Allocate registers for the arguments
        # and store the parameter values in them
        for idx, param in enumerate(self._method_params):
            arg_reg = arg_registers[idx]
            self._alloc_reg(arg_reg)
            param_value = self._load_addr(param)
            self._store(arg_reg, param_value)

        # Clear the method parameters
        self._method_params = []

    def _pop(self, target):
        if self._pcstack:
            # get the return value
            value = None
            if target:
                value = self._load_addr(target)
            # Restore the registers
            self._registers = self._reg_stack.pop()
            # store in the caller return register the value
            self._store(self._returns.pop(), value)
            # restore the last offset from the caller
            self._memory.pop_mp()
            # jump to the return point in the caller
            self._pc = self._pcstack.pop()
            # Restore current method
            self._current_method = self._method_stack.pop()
        else:
            # We reach the end of main function, so return to system
            # with the code returned by main in the return register.
            import sys

            print(end="", flush=True)
            if target is None:
                # void main () was defined, so exit with value 0
                sys.exit(0)
            else:
                sys.exit(self._load_addr(target))

    def _addr(self, var: str):
        if var.startswith("@"):
            return self._globals.get(var)
        return self._registers.get(var)

    def _alloc_reg(self, reg: str):
        if reg not in self._registers:
            self._registers[reg] = self._memory.alloc()

    def _alloc_global(self, varname: str):
        if varname not in self._globals:
            self._globals[varname] = self._memory.alloc()

    def _store_fields(self, fields: dict):
        faddrs = {}
        for field, data in fields.items():
            fvalue = data["value"]
            ftype = data["type"]
            if ftype in ARRAY_TYPES:
                if isinstance(fvalue, (list, str)):
                    fsize = len(fvalue)
                else:
                    fsize = fvalue
                    fvalue = [0] * fsize
                faddr = self._memory.alloc(size=fsize)
                self._memory.store_array(faddr, fsize, fvalue)
            else:
                fsize = 1
                faddr = self._memory.alloc(size=fsize)
                self._memory.store_value(faddr, fvalue)

            faddrs[field] = {"addr": faddr, "type": ftype, "size": fsize}
        return faddrs

    def _store(self, var: str, value: Value):
        vaddr = self._addr(var)
        self._memory.store_value(vaddr, value)

    def _store_addr(self, addr: str, value: Value):
        self._memory.store_value(addr, value)

    def _load(self, var: str) -> Value:
        vaddr = self._addr(var)
        return self._memory.load_value(vaddr)

    def _load_addr(self, addr: str):
        return self._memory.load_value(addr)

    #
    # Execution of operations
    #

    def run(self, ircode: List[Instruction]):
        """Run intermediate code in the interpreter.
        ircode is a list of instruction tuples.
        Each instruction (opcode, *args) is
        dispatched to a method self.run_opcode(*args)
        """

        # Set the code memory region
        self._code = ircode
        self._code_len = len(self._code)

        # Build class templates
        self._class_templates = {}
        self._build_class_templates()

        # Set the memory pointers to the initial state
        # (entrypoint = main())
        self._pc = self._start
        while True:
            try:
                curr_inst = self._next_instruction()
            except IndexError:
                break

            raw_op, args = self._unpack_instruction(curr_inst)

            if len(args) > 0 or raw_op in ["return_void", "print_void"]:
                opcode, modifiers = self._extract_operation(raw_op)
                runner_name = "run_" + opcode
                try:
                    runner = getattr(self, runner_name)
                    runner(*args, modifier=modifiers)
                except AttributeError:
                    print(f"Warning: No {runner_name} method", flush=True)

    #
    # Binary/Unary Operations (arithmetic, relational, logic)
    #

    @staticmethod
    def binary_op(op):
        def wrapper(self, left, right, target, modifier):
            type_modifier = modifier[0]
            lvalue = self._load(left)
            rvalue = self._load(right)

            # If is a binary op of arrays
            # get the arrays and compare its string representation
            if type_modifier in ARRAY_TYPES:
                lsize = lvalue["size"]
                laddr = lvalue["addr"]
                rsize = rvalue["size"]
                raddr = rvalue["addr"]
                lvalue = "".join(self._memory.load_array(laddr, lsize))
                rvalue = "".join(self._memory.load_array(raddr, rsize))

            tvalue = op(self, lvalue, rvalue)
            self._alloc_reg(target)
            self._store(target, tvalue)

        return wrapper

    @binary_op
    def run_add(self, left, right):
        return left + right

    @binary_op
    def run_sub(self, left, right):
        return left - right

    @binary_op
    def run_mul(self, left, right):
        return left * right

    @binary_op
    def run_div(self, left, right):
        return left // right

    @binary_op
    def run_mod(self, left, right):
        return left % right

    @binary_op
    def run_lt(self, left, right):
        return left < right

    @binary_op
    def run_le(self, left, right):
        return left <= right

    @binary_op
    def run_gt(self, left, right):
        return left > right

    @binary_op
    def run_ge(self, left, right):
        return left >= right

    @binary_op
    def run_eq(self, left, right):
        return left == right

    @binary_op
    def run_ne(self, left, right):
        return left != right

    @binary_op
    def run_and(self, left, right):
        return left and right

    @binary_op
    def run_or(self, left, right):
        return left or right

    def run_not(self, source, target, modifier=None):
        self._alloc_reg(target)
        svalue = self._load(source)
        tvalue = not svalue
        self._store(target, tvalue)

    #
    # Memory Management (alloc, load, store)
    #

    def run_alloc(self, varname, modifier=None):
        # First, we need to allocate a register
        # to store the variable value
        self._alloc_reg(varname)

        type_modifier = modifier[0]
        if type_modifier in PRIMITIVE_TYPES:
            self._store(varname, 0)

        elif type_modifier in ARRAY_TYPES:
            size_modifier = modifier[1]
            size = self._parse_to_type(size_modifier, "int")
            # Allocate memory for the array
            saddr = self._memory.alloc(size=size)

            # Create a struct with the base address and size
            # of the array
            array_struct = {"addr": saddr, "size": size, "type": type_modifier}
            # Store the array struct in memory
            self._store(varname, array_struct)

    def run_store(self, source, target, modifier=None):
        type_modifier = modifier[0]
        # If the source is a Field Access
        # the source_addr is the address of the object field
        if self._is_field_access(source):
            source_addr = self._get_field_addr(source)
        # Otherwise, source_addr is the address stored in source
        else:
            source_addr = self._addr(source)

        # Get the value in the source_addr
        svalue = self._load_addr(source_addr)

        # If the target is a Field Access
        # the target_addr is the address of the object field
        if self._is_field_access(target):
            target_addr = self._get_field_addr(target)
        # If target stores a reference
        # the target_addr is the address stored by self._load(target)
        elif len(modifier) == 2 and modifier[1] == "*":
            target_addr = self._load(target)
        # Otherwise, target_addr is the address stored in target
        else:
            target_addr = self._addr(target)

        # If the source and target are arrays
        # store all array elements in the target
        if len(modifier) == 2 and type_modifier in ARRAY_TYPES:
            tarray = self._load_addr(target_addr)
            # Get the base address of the array
            taddr = tarray["addr"]
            # Get the size of the array
            tsize = tarray["size"]
            # Get all the elements of the source array
            sarray = self._memory.load_array(svalue["addr"], tsize)
            # Store the array in memory
            self._memory.store_array(taddr, tsize, sarray)
        else:
            self._store_addr(target_addr, svalue)

    def run_load(self, varname: str, target: str, modifier=None):
        type_modifier = modifier[0]

        # Alloc the target address
        self._alloc_reg(target)

        # If the varname is a Field Access
        # the var_addr is the address of the object field
        if self._is_field_access(varname):
            var_addr = self._get_field_addr(varname)
        # If varname stores a reference
        # the var_addr is the address stored by self._load(varname)
        elif len(modifier) == 2 and modifier[1] == "*":
            var_addr = self._load(varname)
        # Otherwise, var_addr is the address stored in varname
        else:
            var_addr = self._addr(varname)

        # If the type of the operation is a primitive type
        # get the primitive type from the var_addr
        if type_modifier in PRIMITIVE_TYPES:
            svalue = self._load_addr(var_addr)
            self._store(target, svalue)

        elif type_modifier in ARRAY_TYPES:
            if self._is_field_access(varname):
                svalue = self._get_field_data(varname)
            else:
                svalue = self._load_addr(var_addr)

            taddr = self._addr(target)
            if isinstance(svalue, dict):
                saddr = svalue["addr"]
                size = svalue["size"]
                atype = svalue["type"]
                array = self._memory.load_array(saddr, size)

                # Create a copy of the source array
                # Allocate memory for the global constant array
                aaddr = self._memory.alloc(size=size)
                # Store the array in memory
                self._memory.store_array(aaddr, size, array)
                tvalue = {"addr": aaddr, "size": size, "type": atype}
                self._store_addr(taddr, tvalue)

            # If pvalue is a constant string
            else:
                array = svalue
                size = len(array)
                self._memory.store_array(taddr, size, array)

    def run_literal(self, value, target, modifier=None):
        self._alloc_reg(target)
        self._store(target, self._parse_to_type(value, modifier[0]))

    def run_elem(self, source, index, target, modifier=None):
        self._alloc_reg(target)

        if self._is_field_access(source):
            saddr = self._get_field_addr(source)
        else:
            saddr = self._load(source)

        # Deal with the array case
        if isinstance(saddr, dict):
            # Get the base address of the array
            saddr = saddr["addr"]

        offset = self._load(index)
        taddr = saddr + offset
        self._store(target, taddr)

    def run_get(self, source, target, modifier=None):
        # Alloc a register to the target
        self._alloc_reg(target)

        # Get object case
        if modifier[0] == "field":
            var, field = source.split(".")
            obj: MJClassInstance = self._load(var)
            field_loc = obj.get_field_loc(field)
            field_type = obj.get_field_type(field)

            # Save the field loc in the target register
            # If the field is a primitive type, store the value
            if field_type in PRIMITIVE_TYPES:
                self._store(target, self._load_addr(field_loc))
            # Otherwise, store the address of the field
            else:
                self._store(target, field_loc)

        # Array case
        elif modifier[0] in ARRAY_TYPES:
            # Get the array data structure
            array_struct = self._load(source)
            # Get the base address of the array
            saddr = array_struct["addr"]
            # Store the base address in the target register
            self._store(target, saddr)

    def run_new(self, target, modifier=None):
        # Alloc a register to the target
        self._alloc_reg(target)
        type_modifier = modifier[0]

        # New Object case
        if isinstance(type_modifier, str) and type_modifier.startswith("@"):
            class_template = self._class_templates[type_modifier]

            # store fields in memory and return those locations
            field_locs = self._store_fields(class_template.fields)

            # get addresses of the method entrypoints
            method_locs = {
                method: class_template.methods[method]["entrypoint"]
                for method in class_template.methods
            }

            # Create an object to store the attr and method locations
            # of the new object
            new_object = MJClassInstance(
                name=target,
                template=class_template,
                field_locs=field_locs,
                method_locs=method_locs,
            )

            # Store the object reference in memory
            self._store(target, new_object)

        # Array case
        elif type_modifier in ARRAY_TYPES:
            size_modifier = modifier[1]
            size = self._parse_to_type(size_modifier, "int")
            # Allocate memory for the array
            saddr = self._memory.alloc(size=size)
            self._memory.store_array(saddr, size, [0] * size)

            # Create a struct with the base address and size
            # of the array
            array_struct = {"addr": saddr, "size": size, "type": type_modifier}

            # Store the array struct in memory
            self._store(target, array_struct)

    def run_length(self, source, target, modifier=None):
        # Get the array data structure
        array_struct = self._load(source)
        # Get the size of the array
        size = array_struct["size"]
        # Store the size in the target register
        self._alloc_reg(target)
        self._store(target, size)

    #
    # SO calls (print)
    #

    def run_print(self, source=None, modifier=None):
        if modifier[0] == "void":
            print(flush=True)
            return

        if self._is_field_access(source):
            saddr = self._get_field_addr(source)
        else:
            saddr = self._addr(source)

        if modifier[0] in PRIMITIVE_TYPES:
            pvalue = self._load_addr(saddr)
            print(pvalue, end="", flush=True)
        else:
            if self._is_field_access(source):
                pvalue = self._get_field_data(source)
            else:
                pvalue = self._load_addr(saddr)
            # If pvalue is a constant
            if isinstance(pvalue, dict):
                saddr = pvalue["addr"]
                size = pvalue["size"]
                array = self._memory.load_array(saddr, size)
            # If pvalue is a field
            else:
                array = pvalue

            for c in array:
                print(c, end="", flush=True)

    #
    # Branchs (jump, cbranch, func call)
    #

    def run_define(self, source, args, modifier=None):
        class_name, method = source.split(".")
        self._current_method = method
        if method == "main":
            self._alloc_reg("%0")
            self._store("%0", None)

            # Allocate a special register to store
            # the class instance of the main method
            # parent class singleton
            this_reg = "%this"
            self._alloc_reg(this_reg)

            class_template = self._class_templates[class_name]

            # store fields in memory and return those locations
            field_locs = self._store_fields(class_template.fields)

            # get addresses of the method entrypoints
            method_locs = {
                method: class_template.methods[method]["entrypoint"]
                for method in class_template.methods
            }

            # Create an object to store the attr and method locations
            # of the new object
            new_object = MJClassInstance(
                name=this_reg,
                template=class_template,
                field_locs=field_locs,
                method_locs=method_locs,
            )

            # Store the object reference in memory
            self._store(this_reg, new_object)

        else:
            _regs = [arg[1] for arg in args]
            no_return = False if modifier[0] != "void" else True
            self._push(_regs, no_return)

            # Allocate a special register to store
            # the class instance of the method
            this_reg = "%this"
            self._alloc_reg(this_reg)

            # Use the current object as the %this register
            # inside the called method context
            self._store(this_reg, self._current_object)

    def run_param(self, source, modifier=None):
        self._method_params.append(self._addr(source))

    def run_call(self, source, target, modifier=None):
        self._alloc_reg(target)
        self._returns.append(target)
        self._pcstack.append(self._pc)

        # Save the current method
        # Use it to contextualize the label address
        self._method_stack.append(self._current_method)

        var, method = source.split(".")
        obj: MJClassInstance = self._load(var)
        method_loc = obj.get_method_loc(method)

        # Save the var object to use it as the %this register
        # inside the called method context
        self._current_object = obj

        # Update the program counter to the method entrypoint
        self._pc = method_loc

    def run_cbranch(self, test_expr, true_target, false_target, modifier=None):
        test_value = self._load(test_expr)
        target = true_target if test_value else false_target
        label_addr = self._labels[self._current_method][target]
        self._pc = label_addr

    def run_jump(self, target, modifier=None):
        label_addr = self._labels[self._current_method][target]
        self._pc = label_addr

    def run_return(self, target=None, modifier=None):
        rtarget = self._addr(target) if target else None
        self._pop(rtarget)
