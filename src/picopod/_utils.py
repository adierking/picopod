from base64 import b64decode, b64encode
from collections.abc import Buffer, Iterable
from typing import Final

import lz4.block

from .types import DictTable, ListTable, Table, Value

B64_PREFIX: Final[bytes] = b"b64:"
LZ4_PREFIX: Final[bytes] = b"lz4\0"

# Note, Picotron does not use the standard URL-safe Base64 alphabet. Typically, '+' is
# replaced with '-' and '/' with '_', but Picotron has this switched.
B64_ALTCHARS: Final = b"_-"


def picotron_b64encode(b: Buffer) -> bytes:
    return b64encode(b, altchars=B64_ALTCHARS)


def picotron_b64decode(b: Buffer) -> bytes:
    return b64decode(b, altchars=B64_ALTCHARS)


def compress_lz4(data: Buffer) -> bytes:
    """Type-safe wrapper around lz4.block.compress()."""
    compressed = lz4.block.compress(data, store_size=False)
    assert isinstance(compressed, bytes)
    return compressed


def decompress_lz4(compressed: Buffer, uncompressed_size: int) -> bytes:
    """Type-safe wrapper around lz4.block.decompress()."""
    decompressed = lz4.block.decompress(compressed, uncompressed_size)
    assert isinstance(decompressed, bytes)
    return decompressed


def get_list_part(table: DictTable) -> ListTable:
    # Make a set of all the keys that are actually ints so that we ignore implicit
    # conversions. (TODO: Is there a better way to do this?)
    int_keys = {k for k in table if type(k) is int}

    # All keys in 1..N must be present.
    flat = []
    cur = 1
    while cur in int_keys:
        flat.append(table[cur])
        cur += 1
    return flat


def trim_nils(table: ListTable) -> Iterable[Value]:
    # Lists can have nils in the middle, but not at the end.
    end = len(table)
    while end > 0 and table[end - 1] is None:
        end -= 1
    return (table[i] for i in range(end))


def flatten(table: DictTable) -> Table:
    flat = get_list_part(table)
    return list(trim_nils(flat)) if len(flat) == len(table) else table
