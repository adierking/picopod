"""Support for compressing, decompressing, and working with Picotron userdata."""

from __future__ import annotations

import sys
from array import array
from collections.abc import Buffer
from dataclasses import dataclass
from enum import Enum, Flag, IntEnum, auto
from io import BytesIO
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Literal,
    Self,
    assert_never,
    cast,
    overload,
)

from ._io import ByteOrder, IOBytesExt
from .errors import (
    InvalidColorError,
    InvalidPxuError,
    UnrecognizedTypeError,
    UnsupportedTypeError,
    UserdataError,
)
from .palette import PICOTRON_PALETTE, Palette

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

PXU_MAGIC: Final[bytes] = b"pxu\0"

MTF_BITS_MIN: Final = 1
MTF_BITS_MAX: Final = 6


class DataType(Enum):
    """Userdata data types."""

    U8 = auto()
    """Unsigned 8-bit integers."""
    I16 = auto()
    """Signed 16-bit integers."""
    I32 = auto()
    """Signed 32-bit integers."""
    I64 = auto()
    """Signed 64-bit integers."""
    F64 = auto()
    """64-bit floating-point numbers."""

    @staticmethod
    def parse(s: str) -> DataType:
        """Parse a userdata type string.

        For consistency with Picotron, this accepts both signed and unsigned forms for
        each size and converts to the closest match. (For example, ``i8`` becomes
        ``u8``, but ``u16`` becomes ``i16``.)

        Args:
            s (str): The string to parse.

        Returns:
            The parsed :class:`.DataType`.

        Raises:
            UnrecognizedTypeError:
                The string does not match a known data type.
        """
        datatype = {
            "u8": DataType.U8,
            "i8": DataType.U8,
            "u16": DataType.I16,
            "i16": DataType.I16,
            "u32": DataType.I32,
            "i32": DataType.I32,
            "u64": DataType.I64,
            "i64": DataType.I64,
            "f64": DataType.F64,
        }.get(s.lower())
        if datatype is None:
            raise UnrecognizedTypeError(s)
        return datatype

    @staticmethod
    def _from_pxucode(code: int) -> DataType:
        datatype = {
            3: DataType.U8,
            12: DataType.I16,
            13: DataType.I32,
            14: DataType.I64,
            22: DataType.F64,
        }.get(code)
        if datatype is None:
            msg = f"Unrecognized PXU type code: {code}"
            raise InvalidPxuError(msg)
        return datatype

    @property
    def _pxucode(self) -> int:
        return {
            DataType.U8: 3,
            DataType.I16: 12,
            DataType.I32: 13,
            DataType.I64: 14,
            DataType.F64: 22,
        }[self]

    @property
    def _typecode(self) -> str:
        return {
            DataType.U8: "B",
            DataType.I16: "h",
            DataType.I32: "i",
            DataType.I64: "q",
            DataType.F64: "d",
        }[self]

    def __str__(self) -> str:
        """Return the string corresponding to the data type."""
        return {
            DataType.U8: "u8",
            DataType.I16: "i16",
            DataType.I32: "i32",
            DataType.I64: "i64",
            DataType.F64: "f64",
        }[self]


type IntDataTypeEnum = Literal[DataType.U8, DataType.I16, DataType.I32, DataType.I64]
type FloatDataTypeEnum = Literal[DataType.F64]

type IntDataTypeStr = Literal["u8", "i16", "i32", "i64"]
type FloatDataTypeStr = Literal["f64"]

type IntDataType = IntDataTypeEnum | IntDataTypeStr
type FloatDataType = FloatDataTypeEnum | FloatDataTypeStr


class Compression(IntEnum):
    """Userdata compression formats."""

    RAW = 1
    """Data stored with a PXU header but no compression."""

    MTF = 2
    """Data stored with move-to-front and run-length encoding compression."""

    RLE = 8
    """Data stored with run-length encoding compression."""


class _Flags(Flag):
    SIZE32 = 8


@dataclass
class _PxuHeader:
    datatype: DataType
    compression: Compression
    width: int
    height: int | None
    depth: int | None

    @classmethod
    def read(cls, stream: IOBytesExt) -> Self:
        if stream.read_exact(4) != PXU_MAGIC:
            raise InvalidPxuError

        raw_format = stream.read_u8()
        raw_flags = stream.read_u8()

        if raw_flags & 0xF0 != 0:
            datatype = DataType._from_pxucode(raw_format & 0x3F)  # noqa: SLF001
            dimensions = (raw_format >> 6) + 1
            flags = _Flags(raw_flags & 0xF)
            compression = Compression(raw_flags >> 4)

            if flags & _Flags.SIZE32:
                width = stream.read_u32_le()
                height = stream.read_u32_le() if dimensions >= 2 else None
                depth = stream.read_u32_le() if dimensions >= 3 else None
            else:
                width = stream.read_u8()
                height = stream.read_u8() if dimensions >= 2 else None
                depth = stream.read_u8() if dimensions >= 3 else None
        else:
            # Legacy header
            width = raw_format | (raw_flags << 8) | stream.read_u16_le() << 16
            height = stream.read_u32_le()
            depth = stream.read_u32_le()
            datatype = DataType._from_pxucode(stream.read_u8())  # noqa: SLF001
            compression = Compression.MTF

        return cls(datatype, compression, width, height, depth)

    def write(self, stream: IOBytesExt) -> None:
        stream.write(PXU_MAGIC)

        dimensions = 1
        dimensions += 1 if self.height is not None else 0
        dimensions += 1 if self.depth is not None else 0
        stream.write_u8(((dimensions - 1) << 6) | self.datatype._pxucode)  # noqa: SLF001

        flags = _Flags(0)
        if (
            self.width > 255
            or (self.height and self.height > 255)
            or (self.depth and self.depth > 255)
        ):
            flags |= _Flags.SIZE32
        stream.write_u8((self.compression.value << 4) | flags.value)

        if flags & _Flags.SIZE32:
            stream.write_u32_le(self.width)
            if self.height is not None:
                stream.write_u32_le(self.height)
                if self.depth is not None:
                    stream.write_u32_le(self.depth)
        else:
            stream.write_u8(self.width)
            if self.height is not None:
                stream.write_u8(self.height)
                if self.depth is not None:
                    stream.write_u8(self.depth)


def _read_extended_count(stream: IOBytesExt) -> int:
    count = 0
    b = 0xFF
    while b == 0xFF:
        b = stream.read_u8()
        count += b
    return count


def _write_extended_count(out: array[int], count: int) -> None:
    while count >= 0xFF:
        out.append(0xFF)
        count -= 0xFF
    out.append(count)


def _estimate_mtf_bits(data: Buffer) -> int:
    used_bytes = list(range(256))
    with memoryview(data) as view:
        for b in view:
            used_bytes[b] = 1
    used_count = sum(used_bytes)
    return max(MTF_BITS_MIN, min(MTF_BITS_MAX, used_count.bit_length()))


def _compress_mtf_u8(data: Buffer, bits: int | None) -> array[int]:
    result = array("B")
    if bits is None:
        index_width = _estimate_mtf_bits(data)
    else:
        index_width = max(MTF_BITS_MIN, min(MTF_BITS_MAX, bits))
    result.append(index_width)
    max_index = (1 << index_width) - 1
    max_count = 1 << (8 - index_width)
    values = list(range(256))
    slots = list(range(256))
    with memoryview(data) as view:
        while view:
            value = view[0]
            count = 1
            while count < len(view) and view[count] == value:
                count += 1
            try:
                index = values.index(value)
            except ValueError:
                index = max_index
            clamped_count = min(count, max_count) - 1
            clamped_index = min(index, max_index)
            result.append((clamped_count << index_width) | clamped_index)
            if index >= max_index:
                result.append(value)
                values[slots[max_index - 1]] = value
            else:
                if (i := slots.index(index)) > 0:
                    slots.insert(0, slots.pop(i))
            if count >= max_count:
                _write_extended_count(result, count - max_count)
            view = view[count:]
    return result


def _decompress_mtf_u8(stream: IOBytesExt, uncompressed_size: int) -> array[int]:
    index_width = stream.read_u8()
    if not MTF_BITS_MIN <= index_width <= MTF_BITS_MAX:
        msg = f"Invalid MTF index width: {index_width}"
        raise InvalidPxuError(msg)
    max_index = (1 << index_width) - 1
    max_count = 1 << (8 - index_width)
    values = list(range(256))
    slots = list(range(256))
    result = array("B", b"\0" * uncompressed_size)
    with memoryview(result) as view:
        while view:
            b = stream.read_u8()
            index = b & max_index
            count = (b >> index_width) + 1
            if index == max_index:
                value = stream.read_u8()
                values[slots[max_index - 1]] = value
            else:
                value = values[index]
                if (i := slots.index(index)) > 0:
                    slots.insert(0, slots.pop(i))
            if count == max_count:
                count += _read_extended_count(stream)
            view[:count] = value.to_bytes() * count
            view = view[count:]
    return result


def _compress_rle_u8(data: Buffer) -> array[int]:
    result = array("B")
    result.append(0)  # reserved? meant to be index_width == 0?
    with memoryview(data) as view:
        while view:
            value = view[0]
            count = 1
            while count < len(view) and view[count] == value:
                count += 1
            result.append(min(count, 256) - 1)
            result.append(value)
            if count >= 256:
                _write_extended_count(result, count - 256)
            view = view[count:]
    return result


def _decompress_rle_u8(stream: IOBytesExt, uncompressed_size: int) -> array[int]:
    stream.read_u8()  # reserved? meant to be index_width == 0?
    result = array("B", b"\0" * uncompressed_size)
    with memoryview(result) as view:
        while view:
            count = stream.read_u8() + 1
            value = stream.read_u8()
            if count == 256:
                count += _read_extended_count(stream)
            view[:count] = value.to_bytes() * count
            view = view[count:]
    return result


def _compress_rle_i16(data: Sequence[int]) -> array[int]:
    result = array("B")
    result.append(0)  # reserved? meant to be index_width == 0?
    pos = 0
    while pos < len(data):
        value = data[pos]
        start_pos = pos
        pos += 1
        while pos < len(data) and data[pos] == value:
            pos += 1
        count = pos - start_pos
        result.append(min(count, 256) - 1)
        result.extend(value.to_bytes(2, "little", signed=True))
        if count >= 256:
            _write_extended_count(result, count - 256)
    return result


def _decompress_rle_i16(stream: IOBytesExt, uncompressed_size: int) -> array[int]:
    stream.read_u8()  # reserved? meant to be index_width == 0?
    pos = 0
    result = array("h")
    while pos < uncompressed_size:
        count = stream.read_u8() + 1
        value = stream.read_i16_le()
        if count == 256:
            count += _read_extended_count(stream)
        result.extend([value] * count)
        pos += count
    return result


@dataclass
class _Owned[T: (int, float)]:
    inner: array[T]


class Userdata[T: (int, float)]:
    """Represents a Picotron userdata object."""

    _datatype: DataType
    _width: int
    _height: int | None
    _data: array[T]

    __match_args__: ClassVar = ("datatype", "width", "height", "data")

    @overload
    def __init__(
        self: Userdata[int],
        datatype: IntDataType,
        *,
        data: bytes | bytearray | Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self: Userdata[int],
        datatype: IntDataType,
        width: int,
        *,
        data: bytes | bytearray | Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self: Userdata[int],
        datatype: IntDataType,
        width: int,
        height: int | None,
        data: bytes | bytearray | Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self: Userdata[float],
        datatype: FloatDataType,
        *,
        data: Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self: Userdata[float],
        datatype: FloatDataType,
        width: int,
        *,
        data: Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self: Userdata[float],
        datatype: FloatDataType,
        width: int,
        height: int | None,
        data: Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self,
        datatype: DataType | str,
        *,
        data: bytes | bytearray | Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self,
        datatype: DataType | str,
        width: int,
        *,
        data: bytes | bytearray | Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self,
        datatype: DataType | str,
        width: int,
        height: int | None,
        data: bytes | bytearray | Iterable[T] | _Owned[T],
    ) -> None: ...

    @overload
    def __init__(
        self,
        datatype: DataType | str,
        width: int,
        height: int | None = None,
    ) -> None: ...

    def __init__(
        self,
        datatype: DataType | str,
        width: int | None = None,
        height: int | None = None,
        data: bytes | bytearray | Iterable[T] | _Owned[T] | None = None,
    ) -> None:
        """Construct a new userdata object.

        Args:
            datatype (str|DataType):
                The type of each data value, as either a string or a :class:`DataType`.

                If this is a string, the accepted values mirror Picotron. Somewhat
                confusingly, the sign prefix is ignored, so ``i8`` will always be
                unsigned and ``u16`` will always be signed. This is for compatibility
                with Picotron.

                - ``u8``/``i8``: Unsigned 8-bit integers.
                - ``u16``/``i16``: Signed 16-bit integers.
                - ``u32``/``i32``: Signed 32-bit integers.
                - ``u64``/``i64``: Signed 64-bit integers.
                - ``f64``: 64-bit floating-point numbers.

            width (int, optional):
                The number of columns in the data. Must be greater than zero.

                If ``None`` or unspecified, ``data`` must be set and the userdata's
                width will be set to the length of the data.

            height (int, optional):
                If the userdata is two-dimensional, the number of rows in the data. Must
                be greater than zero if specified.

            data (optional):
                The data to initialize the userdata with. This can be a byte string or
                any iterable sequence like a list. If not provided, the userdata is
                zero-initialized.

                If ``width`` or ``height`` is provided, the data's length must equal
                ``width * height`` or this will raise a :class:`.UserdataError`.

        Raises:
            UnrecognizedTypeError:
                The datatype string does not match a known data type.

            ValueError:
                The width or height is less than 1.
        """
        if isinstance(datatype, str):
            self._datatype = DataType.parse(datatype)
        else:
            self._datatype = datatype

        if width is not None and width <= 0:
            msg = "width must be positive"
            raise ValueError(msg)
        if height is not None and height <= 0:
            msg = "height must be positive"
            raise ValueError(msg)

        typecode = self._datatype._typecode  # noqa: SLF001
        if isinstance(data, _Owned):
            # Hack for a private no-copy constructor
            if data.inner.typecode != typecode:
                msg = f"Expected '{typecode}' but got '{data.inner.typecode}'"
                raise ValueError(msg)
            self._data = data.inner
        elif data is not None:
            self._data = array(typecode, data)
        elif width is not None:
            self._data = cast("array[T]", array(typecode, [0] * width * (height or 1)))
        else:
            msg = "Cannot construct userdata without a width or data"
            raise ValueError(msg)

        self._width = width or len(self._data)
        self._height = height
        expected_size = self._width * (self._height or 1)
        if len(self._data) != expected_size:
            msg = f"Expected data with size {expected_size} but got {len(self._data)}"
            raise ValueError(msg)

    @property
    def datatype(self) -> DataType:
        """The :class:`.DataType` of each value."""
        return self._datatype

    @property
    def width(self) -> int:
        """The number of columns in the data."""
        return self._width

    @property
    def height(self) -> int | None:
        """The number of rows in the data if it is 2D, otherwise ``None``."""
        return self._height

    @overload
    @classmethod
    def read_raw(
        cls: type[Userdata[int]],
        stream: IO[bytes],
        datatype: IntDataType,
        width: int,
        height: int | None,
        byteorder: ByteOrder = "big",
    ) -> Userdata[int]: ...

    @overload
    @classmethod
    def read_raw(
        cls: type[Userdata[float]],
        stream: IO[bytes],
        datatype: FloatDataType,
        width: int,
        height: int | None,
        byteorder: ByteOrder = "big",
    ) -> Userdata[float]: ...

    @overload
    @classmethod
    def read_raw(
        cls,
        stream: IO[bytes],
        datatype: DataType | str,
        width: int,
        height: int | None,
        byteorder: ByteOrder = "big",
    ) -> Self: ...

    @classmethod
    def read_raw(
        cls,
        stream: IO[bytes],
        datatype: DataType | str,
        width: int,
        height: int | None,
        byteorder: ByteOrder = "big",
    ) -> Self:
        """Read a raw uncompressed userdata payload from a stream.

        Args:
            stream (IO[bytes]):
                The stream to read from.
            datatype (DataType|str):
                The type of each data value (can be a string or :class:`.DataType`).
            width (int):
                The number of columns in the userdata.
            height (int, optional):
                The number of rows in the userdata.
            byteorder (str, optional):
                The byte order of each element. Defaults to "big".

        Returns:
            The userdata that was read.

        Raises:
            UnrecognizedTypeError: The datatype string does not match a known data type.
        """
        if isinstance(datatype, str):
            datatype = DataType.parse(datatype)
        data = array(datatype._typecode)  # noqa: SLF001
        data.fromfile(stream, width * (height or 1))
        if sys.byteorder != byteorder:
            data.byteswap()
        return cls(datatype, width, height, _Owned(data))

    def write_raw(self, stream: IO[bytes], byteorder: ByteOrder = "big") -> None:
        """Write the userdata's payload to a stream as raw uncompressed bytes.

        Args:
            stream (IO[bytes]): The stream to write to.
            byteorder (str): The byte order of each element. Defaults to "big".
        """
        if sys.byteorder == byteorder:
            self._data.tofile(stream)
        else:
            copy = array(self._data.typecode, self._data)
            copy.byteswap()
            copy.tofile(stream)

    @staticmethod
    def read_pxu(stream: IO[bytes]) -> Userdata[int]:
        """Read PXU-framed userdata from a stream and decompresses it if necessary.

        Args:
            stream (IO[bytes]): The stream to read from.

        Returns:
            The userdata that was read.
        """
        stream = IOBytesExt.wrap(stream)
        header = _PxuHeader.read(stream)
        if header.depth and header.depth > 1:
            msg = "3D userdata is not supported"
            raise UserdataError(msg)

        uncompressed_size = header.width * (header.height or 1)
        match header.compression:
            case Compression.RAW if header.datatype == DataType.U8:
                # I tested non-u8 raw data with Picotron 0.2.1c and it didn't handle it
                # correctly because it uses width * height to calculate the total size.
                # There doesn't seem to be any way to get pod() to emit non-u8 raw data
                # anyway, so for now we restrict this to u8.
                return Userdata.read_raw(
                    stream, header.datatype, header.width, header.height
                )

            case Compression.RAW:
                msg = "Raw data is only supported for U8 userdata"
                raise InvalidPxuError(msg)

            case Compression.MTF if header.datatype == DataType.U8:
                data = _decompress_mtf_u8(stream, uncompressed_size)

            case Compression.MTF:
                msg = "MTF compression is only supported for U8 userdata"
                raise InvalidPxuError(msg)

            case Compression.RLE if header.datatype == DataType.U8:
                data = _decompress_rle_u8(stream, uncompressed_size)

            case Compression.RLE if header.datatype == DataType.I16:
                data = _decompress_rle_i16(stream, uncompressed_size)

            case Compression.RLE:
                msg = "RLE compression is only supported for U8 and I16 userdata"
                raise InvalidPxuError(msg)

            case unexpected:
                assert_never(unexpected)

        return Userdata(header.datatype, header.width, header.height, _Owned(data))

    def write_pxu(
        self,
        stream: IO[bytes],
        compression_hint: Compression = Compression.MTF,
    ) -> None:
        """Write PXU-framed userdata to a stream and compress it as requested.

        Args:
            stream (IO[bytes]):
                The stream to write to.

            compression_hint (Compression, optional):
                A hint for the type of compression to use. If the data type does not
                support the requested compression, the hint will be ignored. Defaults
                to :attr:`~.Compression.MTF`.
        """
        match self._datatype:
            case DataType.U8:
                compression = compression_hint
            case DataType.I16:
                compression = Compression.RLE
            case _:
                raise UnsupportedTypeError(self._datatype)

        stream = IOBytesExt.wrap(stream)
        header = _PxuHeader(
            self._datatype, compression, self._width, self._height, depth=None
        )
        header.write(stream)

        match self._datatype:
            case DataType.U8:
                match header.compression:
                    case Compression.MTF:
                        stream.write(_compress_mtf_u8(self._data, bits=4))
                    case Compression.RLE:
                        stream.write(_compress_rle_u8(self._data))
                    case Compression.RAW:
                        stream.write(self._data)
                    case unexpected:
                        assert_never(unexpected)

            case DataType.I16:
                data = cast("array[int]", self._data)
                stream.write(_compress_rle_i16(data))

    @overload
    @staticmethod
    def from_str(
        datatype: IntDataType,
        width: int,
        height: int | None,
        payload: str,
    ) -> Userdata[int]: ...

    @overload
    @staticmethod
    def from_str(
        datatype: FloatDataType,
        width: int,
        height: int | None,
        payload: str,
    ) -> Userdata[float]: ...

    @overload
    @staticmethod
    def from_str(
        datatype: DataType | str,
        width: int,
        height: int | None,
        payload: str,
    ) -> Userdata[int] | Userdata[float]: ...

    @staticmethod
    def from_str(
        datatype: DataType | str,
        width: int,
        height: int | None,
        payload: str,
    ) -> Userdata[int] | Userdata[float]:
        """Decode a userdata payload string.

        For int-based userdata, the string must contain the bytes for each integer in
        big-endian hexadecimal. For float userdata, it must contain floats separated by
        commas.

        Args:
            datatype (DataType|str): The userdata type to decode as.
            width (int): The number of columns in the userdata.
            height (int, optional): The number of rows in the userdata.
            payload (str): The payload string.

        Returns:
            The decoded userdata.

        Raises:
            UnrecognizedTypeError: The datatype string does not match a known data type.
        """
        if isinstance(datatype, str):
            datatype = DataType.parse(datatype)
        if datatype == DataType.F64:
            floats = (float(f) for f in payload.split(",", width * (height or 1)))
            return Userdata(datatype, width, height, floats)
        else:
            stream = BytesIO(bytes.fromhex(payload))
            return Userdata.read_raw(stream, datatype, width, height)

    def to_str(self) -> str:
        """Encode a userdata payload string.

        For int-based userdata, the string will contain the bytes for each integer in
        big-endian hexadecimal. For float userdata, it will contain floats separated by
        commas.

        Returns:
            The encoded string.
        """
        if self._datatype == DataType.F64:
            return ",".join(str(value) for value in self._data)
        else:
            stream = BytesIO()
            self.write_raw(stream)
            return stream.getvalue().hex()

    @staticmethod
    def from_rgb(
        width: int,
        height: int,
        rgb: Sequence[int],
        palette: Palette = PICOTRON_PALETTE,
    ) -> Userdata[int]:
        """Convert an RGB image into indexed userdata.

        This is the reverse of :meth:`to_rgb()`; every color in the image must exactly
        match one of the colors in the palette or else this will fail.

        Refer to Picopod's encode_image example for a demonstration of how to quantize
        an arbitrary image using Pillow.

        Args:
            width (int):
                The number of columns in the image.
            height (int):
                The number of rows in the image:
            rgb (Sequence[int]):
                A sequence of R, G, B values for each pixel.
            palette (list[tuple[int, int, int]], optional):
                A list of (R, G, B) tuples to look up each pixel in.
                Defaults to the standard Picotron palette if not given.

        Returns:
            A userdata object where each byte is a palette index for a pixel.

        Raises:
            InvalidColorError: A color was not present in the palette.
            ValueError: The image size is invalid or does not match the data.
        """
        if width <= 0:
            msg = "width must be positive"
            raise ValueError(msg)
        if height <= 0:
            msg = "height must be positive"
            raise ValueError(msg)
        expected_size = width * height * 3
        if len(rgb) != expected_size:
            msg = (
                f"Unexpected image data size: expected {expected_size}, got {len(rgb)}"
            )
            raise ValueError(msg)

        palette_map = {}
        for i, color in enumerate(palette):
            if color not in palette_map:
                palette_map[color] = i

        data = array("B", [0] * width * height)
        for pos in range(len(data)):
            r, g, b = rgb[pos * 3 : pos * 3 + 3]
            if not 0 <= r <= 255 or not 0 <= g <= 255 or not 0 <= b <= 255:
                msg = f"Invalid color: ({r}, {g}, {b})"
                raise InvalidColorError(msg)
            value = palette_map.get((r, g, b))
            if value is None:
                msg = f"Color is not in the palette: #{r:02x}{g:02x}{b:02x}"
                raise InvalidColorError(msg)
            data[pos] = value

        return Userdata(DataType.U8, width, height, _Owned(data))

    def to_rgb(self, palette: Palette = PICOTRON_PALETTE) -> bytearray:
        """Convert an indexed image into RGB.

        Args:
            palette (list[tuple[int, int, int]], optional):
                A list of (R, G, B) tuples to index with each value in the userdata.
                Defaults to the standard Picotron palette if not given.

        Returns:
            A byte string of R, G, B values for each pixel.

        Raises:
            InvalidColorError: A color was not present in the palette.
        """
        result = bytearray(self.width * (self.height or 1) * 3)
        for i, color in enumerate(self._data):
            index = int(color)
            if not 0 <= index < len(palette):
                msg = f"Color index is outside the palette: {index}"
                raise InvalidColorError(msg)
            result[i * 3 : i * 3 + 3] = palette[index]
        return result

    def __len__(self) -> int:
        """Return the number of values in the data.

        This is always equivalent to `width` * `height`.
        """
        return len(self._data)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> memoryview: ...

    def __getitem__(self, index: int | slice) -> T | memoryview:
        """Get a single value or slice of values from the data.

        Args:
            index (int|slice):
                A slice or index of the value(s) to retrieve.

        Returns:
            If `index` is a slice, a `memoryview` containing a view over the sliced
            data. Otherwise, the value at the requested index.

        Raises:
            IndexError: The index is out of range.
        """
        if isinstance(index, slice):
            with memoryview(self._data) as view:
                return view[index]
        else:
            return self._data[index]

    @overload
    def __setitem__(self, index: int, value: T) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[T] | Buffer) -> None: ...

    def __setitem__(self, index: int | slice, value: T | Iterable[T] | Buffer) -> None:
        """Set a single value or slice of values in the userdata.

        Args:
            index (int|slice):
                A slice or index of the value(s) to set.
            value (Iterable|Buffer):
                If `index` is a slice, an `Iterable` or `Buffer` of values to assign,
                otherwise a single value.

        Raises:
            IndexError: The index is out of range.
        """
        if isinstance(index, slice):
            if isinstance(value, Buffer):
                with memoryview(self._data) as view:
                    view[index] = value
            else:
                values = cast("Iterable[T]", value)
                indices = index.indices(len(self._data))
                for i, v in zip(range(*indices), values, strict=False):
                    self._data[i] = v
        else:
            self._data[index] = cast("T", value)

    def __iter__(self) -> Iterator[T]:
        """Return an iterator over each value in the userdata."""
        return self._data.__iter__()

    def __buffer__(self, flags: int) -> memoryview:
        """Return a `memoryview` of the userdata."""
        return self._data.__buffer__(flags)

    def __release_buffer__(self, buffer: memoryview) -> None:
        """Release a `memoryview` previously returned by `__buffer__()`."""
        self._data.__release_buffer__(buffer)

    def __copy__(self) -> Userdata[T]:
        """Create a shallow copy of this userdata."""
        return Userdata(self.datatype, self.width, self.height, _Owned[T](self._data))

    def __deepcopy__(self, memo: Any) -> Userdata[T]:  # noqa: ANN401
        """Create a deep copy of this userdata."""
        return Userdata(self.datatype, self.width, self.height, self._data)

    def __eq__(self, other: object) -> bool:
        """Return true if two userdata objects and their contents are equivalent."""
        if not isinstance(other, Userdata):
            return NotImplemented
        return (
            self._datatype == other._datatype
            and self._width == other._width
            and self._height == other._height
            and self._data == other._data
        )

    def __hash__(self) -> int:
        """Return a hash of the userdata object, including its contents."""
        return hash((self._datatype, self._width, self._height, self._data))

    def __repr__(self) -> str:
        """Return a verbose string representation of the userdata object."""
        return (
            f"{self.__class__.__name__}("
            f"{self._datatype!r}, "
            f"{self._width}, "
            f"{self._height}, "
            f"{self._data!r})"
        )
