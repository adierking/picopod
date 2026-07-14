# ruff: noqa: D107

"""Picopod exceptions."""


class Error(Exception):
    """Common base class for all Picopod exceptions."""


class ParserError(Error):
    """Common base class for all parsing-related exceptions."""


class UserdataError(Error):
    """Common base class for all userdata-related exceptions."""


class UnexpectedCharacterError(ParserError):
    """Raised when the pod parser encounters an unexpected character."""

    def __init__(self, pos: int, char: bytes, encoding: str) -> None:
        decoded = char.decode(encoding, "replace")
        super().__init__(f"Unexpected character at pos {pos}: '{decoded}'")


class UnexpectedTokenError(ParserError):
    """Raised when the pod parser encounters an unexpected token."""

    def __init__(self, token: object) -> None:
        super().__init__(f"Unexpected token: '{token}'")


class UnrecognizedEscapeError(ParserError):
    """Raised when the pod parser encounters an unrecognized escape sequence."""

    def __init__(self, pos: int, escape: bytes, encoding: str) -> None:
        decoded = escape.decode(encoding, "replace")
        super().__init__(f"Unrecognized escape at pos {pos}: \\{decoded}")


class InvalidEscapeError(ParserError):
    """Raised when the pod parser encounters an invalid escape sequence."""

    def __init__(self, pos: int, escape: bytes, encoding: str) -> None:
        decoded = escape.decode(encoding, "replace")
        super().__init__(f"Invalid '\\{decoded}' escape at pos {pos}")


class UnrecognizedFunctionError(ParserError):
    """Raised when the pod parser encounters an unrecognized function call."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Unrecognized function: '{name}'")


class EndOfStreamError(ParserError):
    """Raised when the pod parser unexpectedly hits the end of the token stream."""

    def __init__(self) -> None:
        super().__init__("Unexpected end of stream")


class InvalidBinaryStringError(ParserError):
    """Raised when the pod parser hits an invalid binary string."""

    def __init__(self) -> None:
        super().__init__("Invalid binary string")


class UnrecognizedTypeError(UserdataError):
    """Raised when a userdata type string is unrecognized."""

    def __init__(self, datatype: object) -> None:
        super().__init__(self, f"Unrecognized userdata type: '{datatype}'")


class InvalidPxuError(UserdataError):
    """Raised when PXU data is invalid."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "Invalid PXU data")


class UnsupportedTypeError(UserdataError):
    """Raised when a userdata operation does not support the current datatype."""

    def __init__(self, datatype: object) -> None:
        super().__init__(f"Unsupported userdata type: {datatype}")


class InvalidColorError(UserdataError):
    """Raised when a color value in userdata is not present in a palette."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "Color is not in the palette")
