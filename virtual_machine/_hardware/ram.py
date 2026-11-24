# ram.py - the memory controller for the vm.
# every address holds a list of "words" so an instruction packet like
# ["LDA", 5] and plain data can both live in the same address space.

import asyncio

ADDRESS_WIDTH = 3
DEFAULT_SIZE = 256  # toy ram, not actual gigs lol
size = DEFAULT_SIZE


def format_address(index):
    # 0 -> "0x000"
    if not isinstance(index, int):
        raise TypeError(f"address must be an int, got {type(index).__name__}")
    if index < 0:
        raise ValueError(f"address can't be negative: {index}")
    return f"0x{index:0{ADDRESS_WIDTH}x}"


def _build_memory(slots):
    return {format_address(i): [] for i in range(slots)}


memory_space = _build_memory(size)


def reset():
    # wipe everything but keep the same capacity
    for slot in memory_space.values():
        slot.clear()


def resize(slots):
    global size, memory_space
    if not isinstance(slots, int) or slots <= 0:
        raise ValueError("ram size has to be a positive int")
    size = slots
    memory_space = _build_memory(slots)


def normalize(address):
    # int or "0x..." -> the canonical address string
    if isinstance(address, int):
        normalized = format_address(address)
    elif isinstance(address, str):
        if address in memory_space:
            return address
        try:
            normalized = format_address(int(address, 0))
        except ValueError:
            raise KeyError(f"invalid memory address: {address!r}")
    else:
        raise TypeError(f"address must be an int or str, got {type(address).__name__}")

    if normalized not in memory_space:
        raise KeyError(f"Segmentation Fault: Address {address} out of bounds")
    return normalized


def _require(address):
    return normalize(address)


class MemoryAddress:
    def __init__(self, address):
        self.address = address

    def fetch(self):
        """Fetches the raw slot contents."""
        return memory_space.get(self.address)

    def store(self, data):
        """Overwrites this slot with data."""
        return write(self.address, data)

    async def free(self, s: float = 0):
        """ASYNC: Clears the data at this address after s seconds."""
        await asyncio.sleep(s)
        memory_space.get(self.address, []).clear()
        return None


_MISSING = object()


def load(address, data=_MISSING, *extra):
    # load(addr, ["LDA", 5]) and load(addr, "LDA", 5) both give ["LDA", 5]
    addr = _require(address)

    values = []
    if data is not _MISSING:
        if isinstance(data, (list, tuple)):
            values.extend(data)
        else:
            values.append(data)
    values.extend(extra)

    memory_space[addr].extend(values)
    return MemoryAddress(addr)


def write(address, data):
    # overwrite the slot instead of appending
    addr = _require(address)
    if isinstance(data, (list, tuple)):
        memory_space[addr] = list(data)
    else:
        memory_space[addr] = [data]
    return MemoryAddress(addr)


def read(address):
    # raw read, returns None if the address is bad
    try:
        addr = normalize(address)
    except (KeyError, TypeError, ValueError):
        return None
    return memory_space.get(addr)


def peek(address, default=None):
    # last word written at this address (that's what data ops care about)
    slot = read(address)
    if not slot:
        return default
    return slot[-1]


def init(address):
    # modern "read" function
    return MemoryAddress(_require(address))


def dump():
    # handy for debugging
    return {addr: list(words) for addr, words in memory_space.items()}
