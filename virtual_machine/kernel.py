
import virtual_machine._hardware.cpu as CPU
import virtual_machine._hardware.ram as RAM  # imports ma ram.py module


class Kernel:
    def boot(self):
        print("[BOOT] Initializing hardware layers...")

        # we can count its keysssssssssssssssssss
        total_slots = len(RAM.memory_space)
        print(f"[KERNEL] Detected RAM capacity: {total_slots} addressable slots.")
        # boot up cpu
        self.cpu = CPU.run()
