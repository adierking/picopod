import re
from collections.abc import Buffer, Iterator
from dataclasses import dataclass
from enum import Enum, auto
from io import BytesIO
from typing import IO, Final, Self, assert_never

from picopod._io import IOBytesExt
from picopod.types import AnyUserdata

from .errors import (
    InvalidBinaryStringError,
    InvalidEscapeError,
    ParserError,
    UnexpectedCharacterError,
    UnrecognizedEscapeError,
)
from .userdata import PXU_MAGIC, Userdata

_BINARY_STRING_MAGIC: Final[bytes] = b"str\0"


@dataclass
class LeftBrace:
    def __str__(self) -> str:
        return "{"


@dataclass
class RightBrace:
    def __str__(self) -> str:
        return "}"


@dataclass
class LeftBracket:
    def __str__(self) -> str:
        return "["


@dataclass
class RightBracket:
    def __str__(self) -> str:
        return "]"


@dataclass
class LeftParen:
    def __str__(self) -> str:
        return "("


@dataclass
class RightParen:
    def __str__(self) -> str:
        return ")"


@dataclass
class Comma:
    def __str__(self) -> str:
        return ","


@dataclass
class Equals:
    def __str__(self) -> str:
        return "="


@dataclass
class Identifier:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass
class String:
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class Number:
    value: int | float

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class BinaryString:
    value: bytes
    encoding: str

    @classmethod
    def read(cls, stream: IO[bytes], encoding: str) -> Self:
        stream = IOBytesExt(stream)
        try:
            if stream.read_exact(4) != _BINARY_STRING_MAGIC:
                raise InvalidBinaryStringError
            length = stream.read_u32_le()
            return cls(stream.read_exact(length), encoding)
        except (EOFError, OSError) as e:
            raise InvalidBinaryStringError from e

    @staticmethod
    def write(stream: IO[bytes], b: Buffer) -> None:
        stream = IOBytesExt(stream)
        stream.write_exact(_BINARY_STRING_MAGIC)
        with memoryview(b) as view:
            stream.write_u32_le(len(view))
            stream.write_exact(view)

    def __str__(self) -> str:
        return self.value.decode(self.encoding, errors="replace")


@dataclass
class BinaryUserdata:
    data: AnyUserdata

    def __str__(self) -> str:
        return "pxu"


type Token = (
    LeftBrace
    | RightBrace
    | LeftBracket
    | RightBracket
    | LeftParen
    | RightParen
    | Comma
    | Equals
    | Identifier
    | String
    | Number
    | BinaryUserdata
    | BinaryString
)

_SINGLE_CHAR_TOKENS: Final[dict[bytes, Token]] = {
    b"{": LeftBrace(),
    b"}": RightBrace(),
    b"[": LeftBracket(),
    b"]": RightBracket(),
    b"(": LeftParen(),
    b")": RightParen(),
    b",": Comma(),
    b"=": Equals(),
}

_ESCAPE_CHARS: Final = {
    b"a": b"\a",
    b"b": b"\b",
    b"f": b"\f",
    b"n": b"\n",
    b"r": b"\r",
    b"t": b"\t",
    b"v": b"\v",
    b"\\": b"\\",
    b'"': b'"',
    b"'": b"'",
}

_IDENT_REGEX: Final = re.compile(rb"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER_REGEX: Final = re.compile(rb"-?(\d+(\.\d*)?|\.\d+)(e[+-]?\d+)?")
_LINE_COMMENT_REGEX: Final = re.compile(rb"--.*")
_BLOCK_COMMENT_REGEX: Final = re.compile(rb"--\[\[.*?\]\]", re.DOTALL)

_INT_ESCAPE_REGEX: Final = re.compile(rb"\d{1,3}")
_HEX_ESCAPE_REGEX: Final = re.compile(rb"x([A-Fa-f0-9]{2})")
_UNICODE_ESCAPE_REGEX: Final = re.compile(rb"u\{([A-Fa-f0-9]{1,8})\}")
_WHITESPACE_ESCAPE_REGEX: Final = re.compile(rb"z\s*")


def is_identifier(s: bytes) -> bool:
    """Return true if a bytestring is a valid Lua identifier."""
    return _IDENT_REGEX.fullmatch(s) is not None


class _State(Enum):
    DEFAULT = auto()
    STRING = auto()
    ESCAPE = auto()


class Tokenizer(Iterator[Token]):
    _buffer: Buffer
    _encoding: str
    _state: _State
    _pos: int
    _strbytes: bytes
    _strdelim: bytes

    def __init__(
        self,
        code: str | Buffer,
        encoding: str = "p8scii",
        *,
        start_pos: int = 0,
    ) -> None:
        self._buffer = code.encode(encoding) if isinstance(code, str) else code
        self._encoding = encoding
        self._state = _State.DEFAULT
        self._pos = start_pos
        self._strbytes = b""
        self._strdelim = b""

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Token:
        # The memoryview cannot be held open across iterations or else we risk not
        # releasing it if iteration stops early.
        with memoryview(self._buffer) as view:
            end = len(view)
            while self._pos < end:
                cur = view[self._pos :]
                match self._state:
                    case _State.DEFAULT:
                        token = self._next_default(cur)
                    case _State.STRING:
                        token = self._next_string(cur)
                    case _State.ESCAPE:
                        token = self._next_escape(cur)
                    case unexpected:
                        assert_never(unexpected)
                if token is not None:
                    return token

        # Once we have reached the end, we must be in the default state or else
        # something is unterminated.
        match self._state:
            case _State.DEFAULT:
                raise StopIteration
            case _State.STRING:
                msg = "Unterminated string literal"
                raise ParserError(msg)
            case _State.ESCAPE:
                msg = "Unterminated escape sequence"
                raise ParserError(msg)
            case unexpected:
                assert_never(unexpected)

    def _next_default(self, cur: memoryview) -> Token | None:
        ch = bytes(cur[:1])
        if ch.isspace():
            self._pos += 1
        elif ch == b'"' or ch == b"'":
            # Picotron doesn't seem to accept single quotes in pods, but they're valid
            # Lua and supporting them is pretty simple.
            self._strdelim = ch
            self._state = _State.STRING
            self._pos += 1
        elif cur[:4] == PXU_MAGIC:
            stream = BytesIO(cur)
            try:
                data = Userdata.read_pxu(stream)
            except Exception as e:
                msg = "Invalid PXU userdata"
                raise ParserError(msg) from e
            self._pos += stream.tell()
            return BinaryUserdata(data)
        elif cur[:4] == _BINARY_STRING_MAGIC:
            stream = BytesIO(cur)
            bstr = BinaryString.read(stream, self._encoding)
            self._pos += stream.tell()
            return bstr
        elif block_comment := _BLOCK_COMMENT_REGEX.match(cur):
            self._pos += block_comment.end()
        elif line_comment := _LINE_COMMENT_REGEX.match(cur):
            self._pos += line_comment.end()
        elif ident := _IDENT_REGEX.match(cur):
            self._pos += ident.end()
            return Identifier(ident[0].decode("ascii"))
        elif number := _NUMBER_REGEX.match(cur):
            s = number[0]
            value = float(s) if (b"." in s or b"e" in s) else int(s)
            self._pos += number.end()
            return Number(value)
        elif token := _SINGLE_CHAR_TOKENS.get(ch):
            self._pos += 1
            return token
        else:
            raise UnexpectedCharacterError(self._pos, ch, self._encoding)
        return None

    def _next_string(self, cur: memoryview) -> Token | None:
        ch = bytes(cur[:1])
        if ch == self._strdelim:
            decoded = self._strbytes.decode(self._encoding)
            self._strbytes = b""
            self._pos += 1
            self._state = _State.DEFAULT
            return String(decoded)
        elif ch == b"\\":
            self._pos += 1
            self._state = _State.ESCAPE
        else:
            self._strbytes += ch
            self._pos += 1
        return None

    def _next_escape(self, cur: memoryview) -> Token | None:
        ch = bytes(cur[:1])
        if escaped := _ESCAPE_CHARS.get(ch):
            self._strbytes += escaped
            self._pos += 1
        elif digits := _INT_ESCAPE_REGEX.match(cur):
            self._strbytes += int(digits[0]).to_bytes()
            self._pos += digits.end()
        elif ch == b"x":
            if not (hex := _HEX_ESCAPE_REGEX.match(cur)):
                raise InvalidEscapeError(self._pos, ch, self._encoding)
            self._strbytes += int(hex[1], base=16).to_bytes()
            self._pos += hex.end()
        elif ch == b"u":
            if not (hex := _UNICODE_ESCAPE_REGEX.match(cur)):
                raise InvalidEscapeError(self._pos, ch, self._encoding)
            self._strbytes += chr(int(hex[1], base=16)).encode("utf-8")
            self._pos += hex.end()
        elif whitespace := _WHITESPACE_ESCAPE_REGEX.match(cur):
            self._pos += whitespace.end()
        else:
            raise UnrecognizedEscapeError(self._pos, ch, self._encoding)
        self._state = _State.STRING
        return None
