import virtual_machine._hardware.ram as RAM

class CPU:
    def __init__(self):
        self.pc = 0 # prgm counter
        self.acc = 0 # accumulator
        self.is_running = True #ded switc

    def run(self):
        print("[CPU] Starting instruction cycle...")

        while self.is_running:
            addr_str = f"0x{self.pc:03x}"
            instruction_packet = RAM.read(addr_str)
            if instruction_packet is None:
                print(f"[CPU FAULT] Read None at address {addr_str}. Halting.")
                break
            if not instruction_packet:
                self.pc += 1
                continue
            opcode = instruction_packet[0]
            operand = instruction_packet[1] if len(instruction_packet) > 1 else None
            if opcode == 'ADD':
                print(f"[CPU] ADD: Adding {operand} to accumulator ({self.acc})")
                self.acc += operand
                self.pc += 1

            elif opcode == 'SUBT':
                print(f"[CPU] SUBT: Subtracting {operand} from accumulator ({self.acc})")
                self.acc -= operand
                self.pc += 1

            elif opcode == 'CLX':
                print("[CPU] CLX: Clearing accumulator")
                self.acc = 0
                self.pc += 1

            elif opcode == 'JMP':
                print(f"[CPU] JMP: Jumping to address {operand}")
                self.pc = operand  # Direct jump modifies PC

            else:
                raise ValueError(f"[CPU PANIC] Unknown opcode '{opcode}' at {addr_str}")

if __name__ == "__main__":
    # Test execution
    cpu = CPU()
    cpu.run()
