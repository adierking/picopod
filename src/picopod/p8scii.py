"""Provides the `p8scii` encoding for translating strings to/from P8SCII.

Picopod automatically registers the encoding when you import it, but if you need to
manually register it, use :meth:`~picopod.p8scii.register()`.
"""

import codecs
from collections.abc import Buffer, Mapping
from types import MappingProxyType
from typing import Final

CODEC_NAME: Final = "p8scii"

#: All P8SCII characters in byte order.
CHARACTERS: Final = "".join(
    [
        # 00-0F: Control codes
        "".join(chr(i) for i in range(0x10)),
        # 10-1F: JP symbols
        "▮■□⁙⁘‖◀▶「」¥•、。゛゜",
        # 20-7E: Printable ASCII
        "".join(chr(i) for i in range(0x20, 0x7F)),
        # 7F-99: Symbols
        "○█▒🐱⬇░✽●♥☉웃⌂⬅😐♪🅾◆…➡★⧗⬆ˇ∧❎▤▥",
        # 9A-CB: Hiragana
        "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんっゃゅょ",
        # CC-FD: Katakana
        "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンッャュョ",
        # FE-FF: Arcs
        "◜◝",
    ]
)


#: Mapping from Unicode code points to bytes.
CHARMAP: Final[Mapping[int, bytes]] = MappingProxyType(
    {ord(ch): i.to_bytes() for i, ch in enumerate(CHARACTERS)}
)


def isascii(ch: int) -> bool:
    """Return true if a character ordinal is the same in both P8SCII and ASCII."""
    return 0 <= ch <= 0x0F or 0x20 <= ch <= 0x7E


def encode(input: str, errors: str = "strict") -> tuple[bytes, int]:
    """Encode a string to P8SCII bytes.

    Args:
        input (str):
            The string to encode.
        errors (str, optional):
            The scheme to use for error handling. Defaults to "strict".

    Returns:
        A (bytes, length consumed) tuple for the encoded data.
        The length consumed is always the length of the input.
    """
    return (IncrementalEncoder(errors).encode(input, final=True), len(input))


def decode(input: Buffer, errors: str = "strict") -> tuple[str, int]:
    """Decode a string from P8SCII bytes.

    Args:
        input (Buffer):
            The bytes to decode.
        errors (str, optional):
            The scheme to use for error handling. Defaults to "strict".

    Returns:
        A (string, length consumed) tuple for the decoded string.
        The length consumed is always the length of the input.
    """
    with memoryview(input) as view:
        return (IncrementalDecoder(errors).decode(input, final=True), len(view))


class IncrementalEncoder(codecs.IncrementalEncoder):
    """P8SCII incremental encoder."""

    def __init__(self, errors: str = "strict") -> None:  # noqa: D107
        self._handler = codecs.lookup_error(errors)

    def encode(self, input: str, final: bool = False) -> bytes:  # noqa: ARG002, D102
        pos = 0
        result = b""
        while pos < len(input):
            ch = input[pos]
            val = ord(ch)
            if isascii(val):
                result += val.to_bytes()
                pos += 1
            elif (b := CHARMAP.get(val)) is not None:
                result += b
                pos += 1
            else:
                replacement, pos = self._handler(
                    UnicodeEncodeError(
                        CODEC_NAME, input, pos, pos + 1, "No P8SCII equivalent"
                    )
                )
                if pos < 0:
                    pos = max(0, pos + len(input))
                if isinstance(replacement, str):
                    result += encode(replacement)[0]
                else:
                    result += replacement
        return result


class IncrementalDecoder(codecs.IncrementalDecoder):
    """P8SCII incremental decoder."""

    def __init__(self, errors: str = "strict") -> None:  # noqa: D107
        pass

    def decode(self, input: Buffer, final: bool = False) -> str:  # noqa: ARG002, D102
        with memoryview(input) as view:
            return "".join(CHARACTERS[b] for b in view)


class Codec(codecs.Codec):
    """P8SCII codec."""

    def encode(self, input: str, errors: str = "strict") -> tuple[bytes, int]:  # noqa: D102
        return encode(input, errors)

    def decode(self, input: bytes, errors: str = "strict") -> tuple[str, int]:  # noqa: D102
        return decode(input, errors)


class StreamWriter(Codec, codecs.StreamWriter):
    """P8SCII stream writer."""


class StreamReader(Codec, codecs.StreamReader):
    """P8SCII stream reader."""


def getregentry() -> codecs.CodecInfo:
    """Return the :class:`~codecs.CodecInfo` for the `p8scii` encoding."""
    return codecs.CodecInfo(
        name=CODEC_NAME,
        encode=encode,
        decode=decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamwriter=StreamWriter,
        streamreader=StreamReader,
    )


def register() -> None:
    """Register the ``p8scii`` encoding if it is not present."""
    try:
        codecs.lookup(CODEC_NAME)
    except LookupError:
        codecs.register(lambda c: getregentry() if c == CODEC_NAME else None)
