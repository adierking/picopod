"""Provides the ``pod()`` function for serializing objects into Picotron pods."""

import math
import struct
import sys
from collections.abc import Buffer, Mapping, Sequence
from contextlib import suppress
from io import BytesIO
from typing import Final, cast

from picopod._io import IOBytesExt

from ._tokens import BinaryString, is_identifier
from ._utils import (
    B64_PREFIX,
    LZ4_PREFIX,
    compress_lz4,
    get_list_part,
    picotron_b64encode,
    trim_nils,
)
from .types import AnyUserdata, DictTable, ListTable, Value
from .userdata import Compression, DataType, Userdata

_ESCAPE_CHARS: Final = {
    ord("\n"): rb"\n",
    ord("\\"): rb"\\",
    ord('"'): rb"\"",
    # Picotron escapes this because it allows pods to be safely put in
    # `--[[block comments]]` for file metadata.
    ord("]"): rb"\093",
}


def _escape(s: Buffer) -> bytes:
    result: bytes = b""
    with memoryview(s) as view:
        for ch in view:
            if (escape := _ESCAPE_CHARS.get(ch)) is not None:
                result += escape
            elif 0x20 <= ch <= 0x7E:
                result += bytes([ch])
            else:
                result += f"\\{ch:0>3d}".encode("ascii")
    return result


class _PodWriter:
    def __init__(
        self,
        encoding: str,
        invalid_chars: str,
        compression_hint: Compression,
        *,
        binary: bool,
    ) -> None:
        self._encoding = encoding
        self._invalid_chars = invalid_chars
        self._binary = binary
        self._compression_hint = compression_hint
        self._stream = IOBytesExt.wrap(BytesIO())

    def encode(self, s: str) -> bytes:
        return s.encode(self._encoding, errors=self._invalid_chars)

    def write(self, b: Buffer) -> None:
        self._stream.write(b)

    def write_bool(self, value: bool) -> None:
        self.write(b"true" if value else b"false")

    def write_number(self, value: int | float) -> None:
        # Some quirks in Picotron's float handling (as of 0.3.0d):
        #
        # +inf: `pod(math.huge)` returns "inf"
        # -inf: `pod(-math.huge)` returns "-inf"
        # NaN:  `pod(0/0)` returns "1.7976931348623e+308"
        #
        # Note that although ``pod()`` uses "inf" to represent infinity, there is a bug
        # where `unpod()` cannot handle this (it returns nil). For now, just use the
        # largest possible float so that `unpod()` does not fail on data we produce.
        if math.isfinite(value):
            self.write(str(value).encode("ascii"))
        elif value < 0:
            self.write_number(-sys.float_info.max)
        else:
            self.write_number(sys.float_info.max)

    def write_str(self, value: str) -> None:
        self.write(b'"')
        self.write(_escape(self.encode(value)))
        self.write(b'"')

    def write_list(self, values: ListTable) -> None:
        self.write(b"{")
        first = True
        for value in trim_nils(values):
            if not first:
                self.write(b",")
            first = False
            self.write_value(value)
        self.write(b"}")

    def write_dict(self, values: DictTable) -> None:
        # If the dict contains keys 1..N, extract the values to be written at the end
        # without explicit keys.
        list_part = get_list_part(values)
        if len(list_part) == len(values):
            # The entire dict is actually just a list
            self.write_list(list_part)
            return

        # Write the entries that need explicit keys.
        self.write(b"{")
        first = True
        for key, value in values.items():
            if value is None:
                # nil values do not need to be written at all
                continue
            if isinstance(key, int) and key >= 1 and key <= len(list_part):
                continue
            if not first:
                self.write(b",")

            # Keys that aren't identifier strings must be enclosed in brackets.
            first = False
            key_bytes = None
            if isinstance(key, str):
                with suppress(UnicodeEncodeError):
                    key_bytes = key.encode("ascii")
            if key_bytes and is_identifier(key_bytes):
                self.write(key_bytes)
            else:
                self.write(b"[")
                self.write_value(key)
                self.write(b"]")

            self.write(b"=")
            self.write_value(value)

        # Write the "list entries" that have implicit keys.
        for value in trim_nils(list_part):
            if not first:
                self.write(b",")
            first = False
            self.write_value(value)

        self.write(b"}")

    def write_userdata(self, userdata: AnyUserdata) -> None:
        if self._binary and userdata.datatype in (DataType.U8, DataType.I16):
            self.write_binary_userdata(userdata)
        else:
            self.write_text_userdata(userdata)

    def write_binary_userdata(self, userdata: AnyUserdata) -> None:
        userdata.write_pxu(self._stream, self._compression_hint)

    def write_text_userdata(self, userdata: AnyUserdata) -> None:
        self.write(b"userdata(")
        self.write_str(str(userdata.datatype))
        self.write(b",")
        self.write_number(userdata.width)
        self.write(b",")
        if userdata.height is not None:
            self.write_number(userdata.height)
            self.write(b",")
        self.write_str(userdata.to_str())
        self.write(b")")

    def write_bytes(self, b: Buffer) -> None:
        if self._binary:
            BinaryString.write(self._stream, b)
        else:
            self.write(b'"')
            self.write(_escape(b))
            self.write(b'"')

    def write_value(self, value: Value) -> None:
        match value:
            case None:
                self.write(b"nil")
            case bool(_):
                self.write_bool(value)
            case int(_) | float(_):
                self.write_number(value)
            case str(_):
                self.write_str(value)
            case Userdata(_):
                self.write_userdata(cast("AnyUserdata", value))
            case buffer if isinstance(value, Buffer):
                self.write_bytes(cast("Buffer", buffer))
            case mapping if isinstance(value, Mapping):
                self.write_dict(cast("DictTable", mapping))
            case sequence if isinstance(value, Sequence):
                self.write_list(cast("ListTable", sequence))
            case other:
                msg = f"{other.__class__.__name__} objects are not poddable"
                raise TypeError(msg)

    def finish(self, *, lz4: bool = False, base64: bool = False) -> bytes:
        result = self._stream.inner.getvalue()
        if lz4:
            compressed = compress_lz4(result)
            header = LZ4_PREFIX + struct.pack("<ii", len(compressed), len(result))
            result = header + compressed
        if base64:
            result = B64_PREFIX + picotron_b64encode(result)
        return result


def pod(
    value: Value,
    *,
    binary: bool = False,
    lz4: bool = False,
    base64: bool = False,
    compression_hint: Compression = Compression.MTF,
    encoding: str = "p8scii",
    invalid_chars: str = "strict",
) -> bytes:
    """Serialize a Python object into a Picotron pod.

    Args:
        value (Value):
            The value to serialize.

            This can be a :class:`int`, :class:`float`, :class:`bool`, :class:`str`,
            :class:`Buffer` (bytes), :class:`Sequence` (list), :class:`Mapping` (dict),
            :class:`~picopod.Userdata`, or ``None``.

        binary (bool, optional):
            If true, encode userdata as binary when possible, and encode byte objects as
            binary strings. If false, userdata and byte objects will be serialized as
            strings.

            Setting this to true is roughly equivalent to calling Picotron's ``pod()``
            with the 0x1 flag bit (for userdata) or 0x20 flag bit (for strings).

        lz4 (bool, optional):
            If true, LZ4-compress the resulting pod. Defaults to false.

            Setting this to true is equivalent to calling Picotron's ``pod()`` with the
            0x2 flag bit.

        base64 (bool, optional):
            If true, Base64-encode the resulting pod. Defaults to false.

            If ``lz4`` is also true, Base64 encoding applies after compression.

            Note that Picotron's Base64 encoding scheme uses a custom URL-safe variant
            where ``+`` is replaced with ``_`` and ``/`` is replaced with ``-``.

            Setting this to true is equivalent to calling Picotron's ``pod()`` with the
            0x4 flag bit.

        compression_hint (Compression, optional):
            A suggested compression type for binary userdata. If a userdata format does
            not support this type, this parameter is ignored.

            Currently, U8 supports :attr:`~Compression.MTF`, :attr:`~Compression.RLE`,
            and :attr:`~Compression.RAW`, and I16 only supports
            :attr:`~Compression.RLE`. Other formats do not support compression. Defaults
            to :attr:`~Compression.MTF` for maximum compression.

            Specifying raw for this is equivalent to calling Picotron's ``pod()`` with
            the 0x10 flag bit.

        encoding (str, optional):
            The codec to encode strings with. Defaults to "p8scii".

        invalid_chars (str, optional):
            The codec error handler to use for invalid characters in strings.
            Defaults to "strict".

            By default, attempting to encode a string with no valid representation in
            the target encoding (P8SCII by default) will raise an error. Pass "ignore"
            to omit invalid characters altogether, or "replace" to replace them with a
            placeholder (``?`` for P8SCII).

    Returns:
        The serialized pod bytes.

    Raises:
        TypeError:
            The input type cannot be represented in a pod.
        UnicodeEncodeError:
            ``invalid_chars`` is "strict" and a character in a string cannot be
            represented in the target encoding.
    """
    writer = _PodWriter(encoding, invalid_chars, compression_hint, binary=binary)
    writer.write_value(value)
    return writer.finish(lz4=lz4, base64=base64)
