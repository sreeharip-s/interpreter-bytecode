
import virtual_machine._hardware.cpu as CPU
import virtual_machine._hardware.ram as RAM  # imports your ram.py module


class Kernel:
    def boot(self):
        print("[BOOT] Initializing hardware layers...")

        # 1. Access the global memory_space defined in ram.py
        # Since memory_space is a dictionary of addresses, we can count its keys!
        total_slots = len(RAM.memory_space)
        print(f"[KERNEL] Detected RAM capacity: {total_slots} addressable slots.")

        # 2. Hand the RAM module reference (or controller) to the CPU
        # (Assuming your CPU needs a way to read/write via RAM functions)
        self.cpu = CPU(RAM)
        self.file_ops = FileOpHandler()
