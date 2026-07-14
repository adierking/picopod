"""Provides the `unpod()` function for deserializing objects from Picotron pods."""

import codecs
import re
import struct
from collections.abc import Buffer, Callable
from typing import Any, Final, SupportsFloat, SupportsInt, cast, overload

from picopod.types import DictTable, ListTable, Primitive
from picopod.userdata import DataType, Userdata

from ._tokens import (
    BinaryString,
    BinaryUserdata,
    Comma,
    Equals,
    Identifier,
    LeftBrace,
    LeftBracket,
    LeftParen,
    Number,
    RightBrace,
    RightBracket,
    RightParen,
    String,
    Token,
    Tokenizer,
)
from ._utils import B64_PREFIX, LZ4_PREFIX, decompress_lz4, flatten, picotron_b64decode
from .errors import (
    EndOfStreamError,
    ParserError,
    UnexpectedTokenError,
    UnrecognizedFunctionError,
    UnrecognizedTypeError,
)
from .types import AnyUserdata, Table, Value

_COMMENT_REGEX: Final = re.compile(rb"\s*--\[\[.*?\]\]\s*", re.DOTALL)

_CONSTANTS: Final = {
    "nil": None,
    "true": True,
    "false": False,
}


def _decompress_pod(pod: Buffer) -> tuple[Buffer, int]:
    """Decompress a pod.

    The pod may be compressed with LZ4 and/or encoded as Base64. If there is a block
    comment at the beginning of the pod, it will be ignored.

    Args:
        pod: The pod to decompress.

    Returns:
        A tuple containing the resulting buffer and position to start at within it. If
        the data was neither compressed nor encoded, this will return `pod` and the
        position will point past any initial comment.
    """
    decoded = pod
    pos = 0
    with memoryview(pod) as view:
        if bcomment := _COMMENT_REGEX.match(view):
            pos = bcomment.end()
            view = view[pos:]
        if view[:4] == B64_PREFIX:
            decoded = picotron_b64decode(view[4:])
            pos = 0

    with memoryview(decoded) as view:
        # Decompress LZ4
        view = view[pos:]
        if view[:4] == LZ4_PREFIX:
            header, data = view[4:12], view[12:]
            compressed_size, uncompressed_size = struct.unpack("<ii", header)
            decompressed = decompress_lz4(data[:compressed_size], uncompressed_size)
            return (decompressed, 0)
        else:
            return (decoded, pos)


class _Parser:
    type FunctionParser = Callable[[list[Value]], Value]

    _tokens: Tokenizer
    _stack: list[Token]
    _functions: dict[str, FunctionParser]

    def __init__(self, tokens: Tokenizer) -> None:
        self._tokens = tokens
        self._stack = []
        self._functions = {"userdata": self.parse_userdata_call}

    def add_function(self, name: str, parser: FunctionParser) -> None:
        self._functions[name] = parser

    def expect_eof(self) -> None:
        if (token := self.try_peek()) is not None:
            raise UnexpectedTokenError(token)

    def parse_number(self) -> int | float:
        return self.expect(Number).value

    def parse_string(self) -> str:
        return self.expect(String).value

    def parse_constant(self) -> bool | None:
        match self.consume():
            case Identifier(name) as ident:
                if name in _CONSTANTS:
                    return _CONSTANTS[name]
                else:
                    raise UnexpectedTokenError(ident)
            case unexpected:
                raise UnexpectedTokenError(unexpected)

    def parse_table(self) -> Table:
        self.expect(LeftBrace)
        table = {}
        next_index = 1
        done = False
        while not done:
            key = None
            match self.consume():
                case RightBrace():
                    done = True

                case LeftBracket():
                    keyval = self.parse_value()
                    if keyval is None:
                        msg = "Table keys cannot be None"
                        raise ParserError(msg)
                    if not isinstance(keyval, (str, int, float, bool)):
                        msg = "Table keys must be strings, numbers, or booleans"
                        raise ParserError(msg)
                    key = keyval
                    self.expect(RightBracket)
                    self.expect(Equals)

                case Identifier(name) as token:
                    next = self.peek()
                    if isinstance(next, Equals):
                        self.consume()
                        key = name
                    elif (
                        isinstance(next, (Comma, RightBrace)) and name not in _CONSTANTS
                    ):
                        # Weird edge case: Picotron ignores lone unknown identifiers in
                        # tables, seemingly to make it easier to parse metadata. For
                        # example, `{pod,revision=0}` decodes identically to
                        # `{revision=0}`. This is NOT equivalent to treating the value
                        # as nil, which still bumps the current table index, and this
                        # rule does not seem to apply anywhere else.
                        if isinstance(next, Comma):
                            self.consume()
                        continue
                    else:
                        self.push(token)
                        key = next_index
                        next_index += 1

                case other:
                    self.push(other)
                    key = next_index
                    next_index += 1

            if key is not None:
                table[key] = self.parse_value()
                # Ignore up to a single comma. You might say "wait, don't most values
                # have to be followed by commas?" and you would be correct if Picotron
                # did not have a bug/quirk here. `unpod("{1 2 3}")` returns `{1,2,3}`
                # even though it is not valid Lua.
                if isinstance(self.peek(), Comma):
                    self.consume()

        return flatten(table)

    @staticmethod
    def parse_userdata_call(args: list[Value]) -> AnyUserdata:
        if len(args) < 1:
            msg = "Expected userdata type"
            raise ParserError(msg)
        typestr = args[0]
        if not isinstance(typestr, str):
            msg = "Userdata type must be a string"
            raise ParserError(msg)
        try:
            type = DataType.parse(typestr)
        except UnrecognizedTypeError as e:
            msg = "Invalid userdata type"
            raise ParserError(msg) from e

        if len(args) < 2:
            msg = "Expected userdata width"
            raise ParserError(msg)
        width = args[1]
        if not isinstance(width, int):
            msg = "Userdata width must be an integer"
            raise ParserError(msg)

        if len(args) == 3:
            height = None
            data = args[2]
        elif len(args) == 4:
            height = args[2]
            data = args[3]
        else:
            msg = "Too many userdata arguments"
            raise ParserError(msg)
        if height is not None and not isinstance(height, int):
            msg = "Userdata height must be an integer"
            raise ParserError(msg)
        if not isinstance(data, str):
            msg = "Userdata data must be a string"
            raise ParserError(msg)

        try:
            return Userdata.from_str(type, width, height, data)
        except Exception as e:
            msg = "Invalid userdata"
            raise ParserError(msg) from e

    def parse_call(self) -> Value:
        name = self.expect(Identifier).name
        self.expect(LeftParen)
        args = []
        done = False
        while not done:
            if isinstance(self.peek(), RightParen):
                done = True
            else:
                args.append(self.parse_value())
                match token := self.consume():
                    case Comma():
                        if isinstance(self.peek(), RightParen):
                            raise UnexpectedTokenError(token)
                    case RightParen():
                        done = True
                    case unexpected:
                        raise UnexpectedTokenError(unexpected)
        if (parser := self._functions.get(name)) is not None:
            return parser(args)
        else:
            raise UnrecognizedFunctionError(name)

    def parse_value(self) -> Value:
        peek = self.peek()
        match peek:
            case Number(_):
                return self.parse_number()
            case String(_):
                return self.parse_string()
            case LeftBrace():
                return self.parse_table()
            case Identifier(_) as token:
                self.consume()
                peek = self.try_peek()
                self.push(token)
                if peek is not None and isinstance(peek, LeftParen):
                    return self.parse_call()
                else:
                    return self.parse_constant()
            case BinaryUserdata(userdata):
                self.consume()
                return userdata
            case BinaryString(bstr, _):
                self.consume()
                return bstr
            case unexpected:
                raise UnexpectedTokenError(unexpected)

    def try_peek(self) -> Token | None:
        if self._stack:
            return self._stack[-1]
        elif (token := next(self._tokens, None)) is not None:
            self._stack.append(token)
            return token
        else:
            return None

    def peek(self) -> Token:
        if (peek := self.try_peek()) is not None:
            return peek
        else:
            raise EndOfStreamError

    def consume(self) -> Token:
        if self._stack:
            return self._stack.pop()
        elif (token := next(self._tokens, None)) is not None:
            return token
        else:
            raise EndOfStreamError

    def push(self, token: Token) -> None:
        self._stack.append(token)

    def expect[T: Token](self, expected: type[T]) -> T:
        token = self.consume()
        if isinstance(token, expected):
            return token
        else:
            raise UnexpectedTokenError(token)


@overload
def unpod[T: Primitive | AnyUserdata | bytes](
    pod: str | Buffer,
    encoding: str = "p8scii",
    *,
    type: type[T],
) -> T: ...


@overload
def unpod(
    pod: str | Buffer,
    *,
    type: type[list[Any]],
    encoding: str = "p8scii",
) -> ListTable: ...


@overload
def unpod(
    pod: str | Buffer,
    *,
    type: type[dict[Any, Any]],
    encoding: str = "p8scii",
) -> DictTable: ...


@overload
def unpod(
    pod: str | Buffer,
    *,
    type: None = None,
    encoding: str = "p8scii",
) -> Value: ...


def unpod[T: Value](
    pod: str | Buffer,
    *,
    type: type[T] | None = None,
    encoding: str = "p8scii",
) -> T:
    """Deserialize a Picotron pod into a Python object.

    Pods compressed with LZ4 and/or encoded with Base64 are detected and unpacked
    automatically. Whitespace and Lua comments inside the pod are ignored.

    Unlike Picotron, which stops as soon as it reads a valid value, the entire input
    must be consumed or this will raise a :class:`.ParserError`.

    Args:
        pod (str|Buffer):
            The pod to decode, as either a string or bytes.

            If this is a string, it will be automatically encoded to bytes using the
            selected encoding (P8SCII by default).

        type (type, optional):
            The expected result type. If the pod deserializes to a different type, it
            will be converted to this type if supported (see below) or else a
            ``TypeError`` will be raised.

            Supported automatic conversions:

            - ``int``, ``float``, and ``bool`` will all convert to each other.
            - ``str`` will convert to/from ``bytes`` using the selected encoding.
            - ``list`` will convert to ``dict`` with the indexes as keys
              (starting from 1). ``dict`` cannot be converted to ``list``.

        encoding (str, optional):
            The encoding to decode byte strings with.

    Returns:
        The deserialized object. This may be an :class:`int`, :class:`float`,
        :class:`bool`, :class:`str`, :class:`bytes`, :class:`list`, :class:`dict`,
        :class:`~picopod.Userdata`, or ``None`` depending on the type of data in the
        pod. Use the ``type`` parameter to constrain this.

        ``None`` will only be returned if the input decodes to nil. Invalid pods raise a
        :class:`.ParserError` instead of returning ``None``.

    Raises:
        ParserError: An error occurred trying to parse the pod.
        TypeError: The result did not match the required type.
    """
    encoded = pod.encode(encoding) if isinstance(pod, str) else pod
    try:
        buffer, start_pos = _decompress_pod(encoded)
    except Exception as e:
        msg = "Failed to decompress the pod"
        raise ParserError(msg) from e

    # Handles calls to unpod() inside a pod.
    def _call_unpod(args: list[Value]) -> Value:
        if len(args) != 1:
            msg = "unpod() takes exactly one argument"
            raise ParserError(msg)
        pod = args[0]
        if not isinstance(pod, str):
            msg = "unpod() requires a string"
            raise ParserError(msg)
        return unpod(pod)

    parser = _Parser(Tokenizer(buffer, encoding, start_pos=start_pos))
    parser.add_function("unpod", _call_unpod)
    result = parser.parse_value()
    parser.expect_eof()

    # Convenience typecasts to prevent type restrictions from failing unexpectedly
    if type is not None:
        if type is int and isinstance(result, SupportsInt):
            # float -> int
            return cast("T", int(result))
        elif type is float and isinstance(result, SupportsFloat):
            # int -> float
            return cast("T", float(result))
        elif type is bool and isinstance(result, SupportsInt):
            # int|float -> bool
            return cast("T", bool(result))
        elif type is str and isinstance(result, bytes):
            # bytes -> str
            return cast("T", codecs.decode(result, encoding))
        elif type is bytes and isinstance(result, str):
            # str -> bytes
            return cast("T", result.encode(encoding))
        elif type is dict and isinstance(result, list):
            # list -> dict
            return cast("T", {i + 1: v for i, v in enumerate(result)})
        elif not isinstance(result, type):
            msg = f"Expected {type.__name__} but got {result.__class__.__name__}"
            raise TypeError(msg)

    return cast("T", result)
