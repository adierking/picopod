"""Private I/O helpers."""

import struct
from collections.abc import Buffer, Iterable, Iterator
from types import TracebackType
from typing import IO, Literal, cast

type ByteOrder = Literal["big", "little"]


class IOBytesExt[T: IO[bytes]](IO[bytes]):
    """Byte I/O stream extensions.

    This is a proxy class which extends byte I/O streams to include support for reading
    exact numbers of bytes and various integer types.
    """

    def __init__(self, inner: T) -> None:
        self.inner = inner

    def read_exact(self, size: int) -> bytes:
        result = b""
        while len(result) < size:
            read = self.inner.read(size - len(result))
            if len(read) == size:
                return read
            elif len(read) > 0:
                result += read
            else:
                msg = f"Expected {size} bytes"
                raise EOFError(msg)
        return result

    def write_exact(self, buffer: Buffer) -> None:
        with memoryview(buffer) as view:
            while view:
                written = self.inner.write(view)
                if written is None:
                    msg = f"Failed to write {len(view)} bytes"
                    raise OSError(msg)
                view = view[written:]

    def read_u8(self) -> int:
        return self.read_exact(1)[0]

    def read_i8(self) -> int:
        return int.from_bytes(self.read_exact(1), signed=True)

    def read_u16(self, byteorder: ByteOrder) -> int:
        return int.from_bytes(self.read_exact(2), byteorder, signed=False)

    def read_u16_be(self) -> int:
        return self.read_u16("big")

    def read_u16_le(self) -> int:
        return self.read_u16("little")

    def read_i16(self, byteorder: ByteOrder) -> int:
        return int.from_bytes(self.read_exact(2), byteorder, signed=True)

    def read_i16_be(self) -> int:
        return self.read_i16("big")

    def read_i16_le(self) -> int:
        return self.read_i16("little")

    def read_u32(self, byteorder: ByteOrder) -> int:
        return int.from_bytes(self.read_exact(4), byteorder, signed=False)

    def read_u32_be(self) -> int:
        return self.read_u32("big")

    def read_u32_le(self) -> int:
        return self.read_u32("little")

    def read_i32(self, byteorder: ByteOrder) -> int:
        return int.from_bytes(self.read_exact(4), byteorder, signed=True)

    def read_i32_be(self) -> int:
        return self.read_i32("big")

    def read_i32_le(self) -> int:
        return self.read_i32("little")

    def read_u64(self, byteorder: ByteOrder) -> int:
        return int.from_bytes(self.read_exact(8), byteorder, signed=False)

    def read_u64_be(self) -> int:
        return self.read_u64("big")

    def read_u64_le(self) -> int:
        return self.read_u64("little")

    def read_i64(self, byteorder: ByteOrder) -> int:
        return int.from_bytes(self.read_exact(8), byteorder, signed=True)

    def read_i64_be(self) -> int:
        return self.read_i64("big")

    def read_i64_le(self) -> int:
        return self.read_i64("little")

    def read_f32(self, byteorder: ByteOrder) -> float:
        format = ">f" if byteorder == "big" else "<f"
        return cast("float", struct.unpack(format, self.read_exact(4))[0])

    def read_f32_le(self) -> float:
        return self.read_f32("little")

    def read_f32_be(self) -> float:
        return self.read_f32("big")

    def read_f64(self, byteorder: ByteOrder) -> float:
        format = ">d" if byteorder == "big" else "<d"
        return cast("float", struct.unpack(format, self.read_exact(8))[0])

    def read_f64_le(self) -> float:
        return self.read_f64("little")

    def read_f64_be(self) -> float:
        return self.read_f64("big")

    def write_u8(self, value: int) -> None:
        self.write_exact(value.to_bytes(1, signed=False))

    def write_i8(self, value: int) -> None:
        self.write_exact(value.to_bytes(1, signed=True))

    def write_u16(self, value: int, byteorder: ByteOrder) -> None:
        self.write_exact(value.to_bytes(2, byteorder, signed=False))

    def write_u16_be(self, value: int) -> None:
        self.write_u16(value, "big")

    def write_u16_le(self, value: int) -> None:
        self.write_u16(value, "little")

    def write_i16(self, value: int, byteorder: ByteOrder) -> None:
        self.write_exact(value.to_bytes(2, byteorder, signed=True))

    def write_i16_be(self, value: int) -> None:
        self.write_i16(value, "big")

    def write_i16_le(self, value: int) -> None:
        self.write_i16(value, "little")

    def write_u32(self, value: int, byteorder: ByteOrder) -> None:
        self.write_exact(value.to_bytes(4, byteorder, signed=False))

    def write_u32_be(self, value: int) -> None:
        self.write_u32(value, "big")

    def write_u32_le(self, value: int) -> None:
        self.write_u32(value, "little")

    def write_i32(self, value: int, byteorder: ByteOrder) -> None:
        self.write_exact(value.to_bytes(4, byteorder, signed=True))

    def write_i32_be(self, value: int) -> None:
        self.write_i32(value, "big")

    def write_i32_le(self, value: int) -> None:
        self.write_i32(value, "little")

    def write_u64(self, value: int, byteorder: ByteOrder) -> None:
        self.write_exact(value.to_bytes(8, byteorder, signed=False))

    def write_u64_be(self, value: int) -> None:
        self.write_u64(value, "big")

    def write_u64_le(self, value: int) -> None:
        self.write_u64(value, "little")

    def write_i64(self, value: int, byteorder: ByteOrder) -> None:
        self.write_exact(value.to_bytes(8, byteorder, signed=True))

    def write_i64_be(self, value: int) -> None:
        self.write_i64(value, "big")

    def write_i64_le(self, value: int) -> None:
        self.write_i64(value, "little")

    def write_f32(self, value: float, byteorder: ByteOrder) -> None:
        format = ">f" if byteorder == "big" else "<f"
        self.write_exact(struct.pack(format, value))

    def write_f32_le(self, value: float) -> None:
        self.write_f32(value, "little")

    def write_f32_be(self, value: float) -> None:
        self.write_f32(value, "big")

    def write_f64(self, value: float, byteorder: ByteOrder) -> None:
        format = ">d" if byteorder == "big" else "<d"
        self.write_exact(struct.pack(format, value))

    def write_f64_le(self, value: float) -> None:
        self.write_f64(value, "little")

    def write_f64_be(self, value: float) -> None:
        self.write_f64(value, "big")

    @property
    def mode(self) -> str:
        return self.inner.mode

    @property
    def name(self) -> str:
        return self.inner.name

    def close(self) -> None:
        self.inner.close()

    @property
    def closed(self) -> bool:
        return self.inner.closed

    def fileno(self) -> int:
        return self.inner.fileno()

    def flush(self) -> None:
        self.inner.flush()

    def isatty(self) -> bool:
        return self.inner.isatty()

    def read(self, n: int = -1) -> bytes:
        return self.inner.read(n)

    def readable(self) -> bool:
        return self.inner.readable()

    def readline(self, limit: int = -1) -> bytes:
        return self.inner.readline(limit)

    def readlines(self, hint: int = -1) -> list[bytes]:
        return self.inner.readlines(hint)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.inner.seek(offset, whence)

    def seekable(self) -> bool:
        return self.inner.seekable()

    def tell(self) -> int:
        return self.inner.tell()

    def truncate(self, size: int | None = None) -> int:
        return self.inner.truncate(size)

    def writable(self) -> bool:
        return self.inner.writable()

    def write(self, buffer: Buffer) -> int:
        return self.inner.write(buffer)

    def writelines(self, lines: Iterable[Buffer]) -> None:
        self.inner.writelines(lines)

    def __enter__(self) -> "IOBytesExt[IO[bytes]]":
        return IOBytesExt(self.inner.__enter__())

    def __exit__(
        self,
        type: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.inner.__exit__(type, value, traceback)

    def __iter__(self) -> Iterator[bytes]:
        return self.inner.__iter__()

    def __next__(self) -> bytes:
        return self.inner.__next__()
