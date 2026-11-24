# cpu.py - the actual processor.
# an instruction is just a packet in ram: ["LDA", 5], ["OUT"], ["HLT"], etc.
# the assembler turns labels into numbers before we ever get here.

import virtual_machine._hardware.ram as RAM


class CPU:
    def __init__(self, ram=None, trace=False):
        self.ram = ram if ram is not None else RAM
        self.pc = 0  # prgm counter
        self.acc = 0  # accumulator
        self.is_running = True  # ded switc
        self.trace = trace
        self.zero = False  # flag from CMP
        self.less = False  # acc < operand
        self.steps = 0

    # ------------------------- little helpers -------------------------
    def _address(self, pc=None):
        return self.ram.format_address(self.pc if pc is None else pc)

    def _to_number(self, value):
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return int(value, 0)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    raise ValueError(f"expected a number, got {value!r}")
        raise TypeError(f"expected a number, got {type(value).__name__}")

    def _immediate(self, opcode, operand):
        if operand is None:
            raise ValueError(f"{opcode} needs an operand")
        return self._to_number(operand)

    def _memory(self, opcode, operand):
        if operand is None:
            raise ValueError(f"{opcode} needs an address")
        return self.ram.peek(operand, 0)

    def _address_operand(self, opcode, operand):
        address = int(self._to_number(operand))
        if not 0 <= address < self.ram.size:
            raise ValueError(f"{opcode} target {address} is outside RAM")
        return address

    def _advance(self):
        self.pc += 1

    def _jump_if(self, condition, opcode, operand):
        if condition:
            self.pc = self._address_operand(opcode, operand)
        else:
            self._advance()

    def _set_flags(self, left, right):
        self.zero = left == right
        self.less = left < right

    def _divide(self, left, right, integer=False):
        if right == 0:
            raise ZeroDivisionError("division by zero")
        return left // right if integer else left / right

    # --------------------------- execution ----------------------------
    def step(self):
        # run one instruction. returns False once we halt
        if not self.is_running:
            return False

        addr_str = self._address()
        packet = self.ram.read(addr_str)

        if packet is None:
            if self.trace:
                print(f"[CPU FAULT] Read None at address {addr_str}. Halting.")
            self.is_running = False
            return False

        if not packet:
            # empty slot = nop
            self._advance()
            self.steps += 1
            return True

        opcode = str(packet[0]).upper()
        operand = packet[1] if len(packet) > 1 else None

        if opcode == "NOP":
            self._advance()

        elif opcode in ("LDA", "LOAD"):
            self.acc = self._immediate(opcode, operand)
            self._advance()

        elif opcode in ("LDM", "LOADM"):
            self.acc = self._memory(opcode, operand)
            self._advance()

        elif opcode == "STA":
            if operand is None:
                raise ValueError("STA needs an address")
            self.ram.write(operand, self.acc)
            self._advance()

        elif opcode == "ADD":
            self.acc += self._immediate(opcode, operand)
            self._advance()

        elif opcode == "ADDM":
            self.acc += self._memory(opcode, operand)
            self._advance()

        elif opcode in ("SUBT", "SUB"):
            self.acc -= self._immediate(opcode, operand)
            self._advance()

        elif opcode == "SUBM":
            self.acc -= self._memory(opcode, operand)
            self._advance()

        elif opcode == "MUL":
            self.acc *= self._immediate(opcode, operand)
            self._advance()

        elif opcode == "MULM":
            self.acc *= self._memory(opcode, operand)
            self._advance()

        elif opcode == "DIV":
            self.acc = self._divide(self.acc, self._immediate(opcode, operand))
            self._advance()

        elif opcode == "DIVM":
            self.acc = self._divide(self.acc, self._memory(opcode, operand))
            self._advance()

        elif opcode == "IDIV":
            self.acc = self._divide(self.acc, self._immediate(opcode, operand), integer=True)
            self._advance()

        elif opcode == "IDIVM":
            self.acc = self._divide(self.acc, self._memory(opcode, operand), integer=True)
            self._advance()

        elif opcode == "MOD":
            right = self._immediate(opcode, operand)
            if right == 0:
                raise ZeroDivisionError("modulo by zero")
            self.acc %= right
            self._advance()

        elif opcode == "MODM":
            right = self._memory(opcode, operand)
            if right == 0:
                raise ZeroDivisionError("modulo by zero")
            self.acc %= right
            self._advance()

        elif opcode == "CMP":
            self._set_flags(self.acc, self._immediate(opcode, operand))
            self._advance()

        elif opcode == "CMPM":
            self._set_flags(self.acc, self._memory(opcode, operand))
            self._advance()

        elif opcode == "CLX":
            self.acc = 0
            self._advance()

        elif opcode == "INC":
            self.acc += 1
            self._advance()

        elif opcode == "DEC":
            self.acc -= 1
            self._advance()

        elif opcode == "JMP":
            self.pc = self._address_operand(opcode, operand)

        elif opcode in ("JZ", "JE"):
            self._jump_if(self.zero, opcode, operand)

        elif opcode in ("JNZ", "JNE"):
            self._jump_if(not self.zero, opcode, operand)

        elif opcode == "JLT":
            self._jump_if(self.less, opcode, operand)

        elif opcode == "JGT":
            self._jump_if(not self.less and not self.zero, opcode, operand)

        elif opcode == "JLE":
            self._jump_if(self.less or self.zero, opcode, operand)

        elif opcode == "JGE":
            self._jump_if(not self.less, opcode, operand)

        elif opcode == "OUT":
            print(self.acc)
            self._advance()

        elif opcode == "OUTS":
            print(operand if operand is not None else "")
            self._advance()

        elif opcode == "OUTNL":
            print()
            self._advance()

        elif opcode in ("HLT", "HALT", "STOP"):
            self.is_running = False

        else:
            raise ValueError(f"[CPU PANIC] Unknown opcode '{opcode}' at {addr_str}")

        self.steps += 1
        if self.trace:
            shown = "" if operand is None else " " + repr(operand)
            print(f"[CPU] {addr_str}: {opcode}{shown} -> acc={self.acc!r} pc={self.pc}")
        return self.is_running

    def run(self, max_steps=100_000):
        # keep going until HLT (or until we've clearly looped forever)
        while self.is_running:
            if max_steps is not None and self.steps >= max_steps:
                raise RuntimeError(
                    f"hit the {max_steps} instruction limit, possible infinite loop"
                )
            if not self.step():
                break
        return self.acc


if __name__ == "__main__":
    # tiny self test: 5 + 3 - 2 = 6
    RAM.reset()
    RAM.load("0x000", "LDA", 5)
    RAM.load("0x001", "ADD", 3)
    RAM.load("0x002", "SUBT", 2)
    RAM.load("0x003", "OUT")
    RAM.load("0x004", "HLT")
    CPU(RAM, trace=True).run()
