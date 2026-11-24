# assembler.py - turns assembly text into instruction packets for ram.
# two passes:
#   1. work out where every label actually lives
#   2. go back and swap label operands for those addresses

import ast
import re

import virtual_machine._hardware.ram as RAM


class AssemblerError(SyntaxError):
    pass


class Program:
    def __init__(self, instructions, data, labels, entry=0):
        self.instructions = instructions  # [(address, ["LDA", 5]), ...]
        self.data = data                  # {address: value}
        self.labels = labels
        self.entry = entry

    def load_into(self, ram=None, reset=True):
        ram = ram if ram is not None else RAM
        if reset:
            ram.reset()
        for address, packet in self.instructions:
            ram.write(address, packet)
        for address, value in self.data.items():
            ram.write(address, value)
        return self

    def disassemble(self):
        reverse = {}
        for name, addr in self.labels.items():
            reverse.setdefault(addr, []).append(name)

        entries = [(a, "code", p) for a, p in self.instructions]
        entries += [(a, "data", v) for a, v in self.data.items()]

        lines = []
        for address, kind, value in sorted(entries, key=lambda x: x[0]):
            names = reverse.get(address)
            tag = ", ".join(sorted(names)) + ": " if names else ""
            if kind == "code":
                opcode = value[0]
                operand = value[1] if len(value) > 1 else None
                text = opcode if operand is None else f"{opcode} {operand!r}"
            else:
                text = f".word {value!r}"
            lines.append(f"0x{address:03x}: {tag}{text}")
        return "\n".join(lines)


_LABEL_RE = re.compile(r"^([A-Za-z_.][\w.]*)\s*:\s*(.*)$")


class Assembler:
    OPCODES = {
        "NOP", "LDA", "LOAD", "LDM", "LOADM", "STA",
        "ADD", "ADDM", "SUBT", "SUB", "SUBM",
        "MUL", "MULM", "DIV", "DIVM", "IDIV", "IDIVM", "MOD", "MODM",
        "CMP", "CMPM", "CLX", "INC", "DEC",
        "JMP", "JZ", "JE", "JNZ", "JNE", "JLT", "JGT", "JLE", "JGE",
        "OUT", "OUTS", "OUTNL", "HLT", "HALT", "STOP",
    }

    NO_OPERAND = {
        "NOP", "CLX", "INC", "DEC",
        "OUT", "OUTNL", "HLT", "HALT", "STOP",
    }

    DATA_OPS = {
        ".WORD", "DW", "DB", ".BYTE",
        ".SPACE", ".BLOCK", "RESB",
        ".STRING", ".ASCIZ",
    }

    def assemble(self, source):
        statements = self._parse(source)

        code_count = sum(
            1 for s in statements if s["section"] == "code" and s["opcode"]
        )
        data_base = code_count + 1

        labels = {}
        code_addr = 0
        data_offset = 0

        # first pass: label addresses
        for s in statements:
            if s["label"]:
                if s["label"] in labels:
                    raise AssemblerError(
                        f"duplicate label '{s['label']}' on line {s['line']}"
                    )
                if s["section"] == "code":
                    labels[s["label"]] = code_addr
                else:
                    labels[s["label"]] = data_base + data_offset

            if not s["opcode"]:
                continue

            if s["section"] == "code":
                code_addr += 1
            else:
                directive = s["opcode"].upper()
                if directive not in self.DATA_OPS:
                    raise AssemblerError(
                        f"unknown data directive '{s['opcode']}' on line {s['line']}"
                    )
                if directive in (".SPACE", ".BLOCK", "RESB"):
                    data_offset += self._literal_int(s["operand"], s["line"])
                else:
                    data_offset += 1

        if data_base + data_offset > RAM.size:
            raise AssemblerError(
                f"program is too big: needs {data_base + data_offset} slots, "
                f"ram only has {RAM.size}"
            )

        # second pass: build the actual packets
        instructions = []
        data = {}
        code_addr = 0
        data_offset = 0

        for s in statements:
            if not s["opcode"]:
                continue

            if s["section"] == "code":
                opcode = s["opcode"].upper()
                if opcode not in self.OPCODES:
                    raise AssemblerError(
                        f"unknown opcode '{s['opcode']}' on line {s['line']}"
                    )
                operand = self._resolve_operand(
                    opcode, s["operand"], labels, s["line"]
                )
                packet = [opcode] if operand is None else [opcode, operand]
                instructions.append((code_addr, packet))
                code_addr += 1
                continue

            directive = s["opcode"].upper()
            address = data_base + data_offset

            if directive in (".SPACE", ".BLOCK", "RESB"):
                count = self._literal_int(s["operand"], s["line"])
                for i in range(count):
                    data[address + i] = 0
                data_offset += count

            elif directive in (".STRING", ".ASCIZ"):
                data[address] = self._parse_string(s["operand"], s["line"])
                data_offset += 1

            else:
                data[address] = self._resolve_data_value(
                    s["operand"], labels, s["line"]
                )
                data_offset += 1

        return Program(instructions, data, labels)

    # ----------------------------- parsing -----------------------------
    def _parse(self, source):
        statements = []
        section = "code"

        for lineno, raw in enumerate(source.splitlines(), 1):
            line = self._strip_comment(raw).strip()
            if not line:
                continue

            lower = line.lower()
            if lower in (".data", "data"):
                section = "data"
                continue
            if lower in (".code", ".text", "code", "text"):
                section = "code"
                continue
            if lower.startswith("section "):
                name = lower.split(None, 1)[1].strip()
                if name in ("data", ".data"):
                    section = "data"
                    continue
                if name in ("code", "text", ".code", ".text"):
                    section = "code"
                    continue

            # labels can stack and can sit in front of an instruction
            while True:
                match = _LABEL_RE.match(line)
                if not match:
                    break
                statements.append({
                    "section": section,
                    "label": match.group(1),
                    "opcode": None,
                    "operand": None,
                    "line": lineno,
                })
                line = match.group(2).strip()
                if not line:
                    break

            if not line:
                continue

            parts = line.split(None, 1)
            statements.append({
                "section": section,
                "label": None,
                "opcode": parts[0],
                "operand": parts[1].strip() if len(parts) > 1 else None,
                "line": lineno,
            })

        return statements

    def _strip_comment(self, line):
        # ; and # start comments, but not inside strings
        quote = None
        escaped = False
        for i, char in enumerate(line):
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
            elif char in ("'", '"'):
                quote = char
            elif char in (";", "#"):
                return line[:i]
        return line

    # --------------------------- operands ------------------------------
    def _resolve_operand(self, opcode, operand, labels, line):
        if opcode in self.NO_OPERAND:
            if operand is not None:
                raise AssemblerError(f"{opcode} doesn't take an operand (line {line})")
            return None

        if operand is None:
            raise AssemblerError(f"{opcode} needs an operand (line {line})")

        if opcode == "OUTS":
            return self._parse_string(operand, line)

        return self._resolve_value(operand, labels, line)

    def _resolve_data_value(self, operand, labels, line):
        if operand is None:
            raise AssemblerError(f"data directive needs a value (line {line})")
        if operand[:1] in ("'", '"'):
            return self._parse_string(operand, line)
        return self._resolve_value(operand, labels, line)

    def _resolve_value(self, text, labels, line):
        text = text.strip()
        if text in labels:
            return labels[text]
        try:
            return int(text, 0)
        except ValueError:
            raise AssemblerError(
                f"unknown label or bad number '{text}' on line {line}"
            )

    def _parse_string(self, text, line):
        if text is None:
            raise AssemblerError(f"expected a string on line {line}")
        try:
            value = ast.literal_eval(text.strip())
        except (ValueError, SyntaxError):
            raise AssemblerError(f"bad string literal {text!r} on line {line}")
        if not isinstance(value, str):
            raise AssemblerError(f"expected a string, got {value!r} on line {line}")
        return value

    def _literal_int(self, text, line):
        try:
            value = int(text, 0)
        except (TypeError, ValueError):
            raise AssemblerError(f"expected a number, got {text!r} on line {line}")
        if value < 0:
            raise AssemblerError(f"size can't be negative on line {line}")
        return value
