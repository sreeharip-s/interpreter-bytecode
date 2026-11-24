# has an independent memory controler.
size = 8 #gigs
# ---------------------------------------------
memory_space = {f"0x{i:03x}": [] for i in range(size+1)}

import asyncio
class MemoryAddress:
    def __init__(self, address: str):
        self.address = address

    def fetch(self):
        """Fetches the data stored at this memory address."""
        return memory_space.get(self.address)

    async def free(self, s: float = 0):
        """ASYNC: Clears the data at this address after s seconds."""
        await asyncio.sleep(s)
        if self.address in memory_space:
            memory_space[self.address].clear()
            return None
        else:
            #i don't wanna be mean to future me
            return None

def load(address: str, data) -> MemoryAddress:
    if address not in memory_space:
        raise KeyError(f"Segmentation Fault: Address {address} out of bounds")
    memory_space[address].append(data)
    return MemoryAddress(address)

def init(address: str):
    # modern "read" function
    return MemoryAddress(address)

def read(address: str):
    # raw reads data for the kernel to manually check the size of the ram
    return memory_space.get(address, None)
