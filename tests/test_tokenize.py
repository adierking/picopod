from collections.abc import Buffer

import pytest

from picopod._tokens import (
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
from picopod.errors import (
    InvalidBinaryStringError,
    InvalidEscapeError,
    ParserError,
    UnexpectedCharacterError,
    UnrecognizedEscapeError,
)
from picopod.userdata import DataType, Userdata


def tokenize(code: str | Buffer, encoding: str = "p8scii") -> list[Token]:
    return list(Tokenizer(code, encoding))


def test_tokenize_symbols() -> None:
    assert tokenize("{}[](),=") == [
        LeftBrace(),
        RightBrace(),
        LeftBracket(),
        RightBracket(),
        LeftParen(),
        RightParen(),
        Comma(),
        Equals(),
    ]
    with pytest.raises(UnexpectedCharacterError):
        tokenize("!")


def test_tokenize_ident() -> None:
    assert tokenize("a") == [Identifier("a")]
    assert tokenize("A") == [Identifier("A")]
    assert tokenize("_") == [Identifier("_")]
    assert tokenize("abcdefg") == [Identifier("abcdefg")]
    assert tokenize("AbCdEfG") == [Identifier("AbCdEfG")]
    assert tokenize("_a_b_c_") == [Identifier("_a_b_c_")]
    assert tokenize("_0123456789") == [Identifier("_0123456789")]
    assert tokenize("baadf00d") == [Identifier("baadf00d")]
    assert tokenize("4b1d") == [Number(4), Identifier("b1d")]


def test_tokenize_number() -> None:
    assert tokenize("0") == [Number(0)]
    assert tokenize("1") == [Number(1)]
    assert tokenize("-1") == [Number(-1)]
    assert tokenize("0123456789") == [Number(123456789)]
    assert tokenize("-0123456789") == [Number(-123456789)]
    assert tokenize(".1") == [Number(0.1)]
    assert tokenize("-.1") == [Number(-0.1)]
    assert tokenize("0.1") == [Number(0.1)]
    assert tokenize("-0.1") == [Number(-0.1)]
    assert tokenize("123.") == [Number(123.0)]
    assert tokenize("-123.") == [Number(-123.0)]
    assert tokenize("123.0") == [Number(123.0)]
    assert tokenize("-123.0") == [Number(-123.0)]
    assert tokenize("123.456") == [Number(123.456)]
    assert tokenize("-123.456") == [Number(-123.456)]
    assert tokenize("1e0") == [Number(1)]
    assert tokenize("1e-0") == [Number(1)]
    assert tokenize("1e2") == [Number(100.0)]
    assert tokenize("-1e2") == [Number(-100.0)]
    assert tokenize("1e+2") == [Number(100.0)]
    assert tokenize("-1e+2") == [Number(-100.0)]
    assert tokenize("1e-2") == [Number(0.01)]
    assert tokenize("-1e-2") == [Number(-0.01)]
    assert tokenize("1.5e2") == [Number(150.0)]
    assert tokenize("-1.5e2") == [Number(-150.0)]
    assert tokenize("1e10") == [Number(10000000000.0)]
    assert tokenize("1e-10") == [Number(0.0000000001)]
    assert tokenize("1e") == [Number(1), Identifier("e")]
    assert tokenize("e1") == [Identifier("e1")]
    with pytest.raises(UnexpectedCharacterError):
        tokenize(".")
    with pytest.raises(UnexpectedCharacterError):
        tokenize("-.")


def test_tokenize_string() -> None:
    assert tokenize('""') == [String("")]
    assert tokenize("''") == [String("")]
    assert tokenize('"hello!"') == [String("hello!")]
    assert tokenize("'hello!'") == [String("hello!")]
    assert tokenize('"\'"') == [String("'")]
    assert tokenize("'\"'") == [String('"')]
    assert tokenize(r"'\a'") == [String("\x07")]
    assert tokenize(r"'\b'") == [String("\x08")]
    assert tokenize(r"'\f'") == [String("\x0c")]
    assert tokenize(r"'\n'") == [String("\x0a")]
    assert tokenize(r"'\r'") == [String("\x0d")]
    assert tokenize(r"'\t'") == [String("\x09")]
    assert tokenize(r"'\v'") == [String("\x0b")]
    assert tokenize(r"'\\'") == [String("\x5c")]
    assert tokenize(r"'\"'") == [String("\x22")]
    assert tokenize(r"'\''") == [String("\x27")]
    assert tokenize(r"'\9'") == [String("\x09")]
    assert tokenize(r"'\09'") == [String("\x09")]
    assert tokenize(r"'\009'") == [String("\x09")]
    assert tokenize(r"'\0099'") == [String("\x09" + "9")]
    assert tokenize(r"'\x0a'") == [String("\x0a")]
    assert tokenize(r"'\x0A'") == [String("\x0a")]
    assert tokenize(r"'\u{1f643}'", encoding="utf-8") == [String("\U0001f643")]
    assert tokenize(r"'\xf0\x9f\x99\x83'", encoding="utf-8") == [String("\U0001f643")]
    assert tokenize("'Hello, \\zworld!'") == [String("Hello, world!")]
    assert tokenize("'Hello, \\z \t\r\nworld!'") == [String("Hello, world!")]
    assert tokenize(r"'line 1\r\nline 2\r\nline 3\r\n'") == [
        String("line 1\r\nline 2\r\nline 3\r\n")
    ]
    with pytest.raises(UnrecognizedEscapeError):
        tokenize(r"'\q'")
    with pytest.raises(InvalidEscapeError):
        tokenize(r"'\x'")
    with pytest.raises(InvalidEscapeError):
        tokenize(r"'\x0'")
    with pytest.raises(InvalidEscapeError):
        tokenize(r"'\u'")
    with pytest.raises(InvalidEscapeError):
        tokenize(r"'\u{'")
    with pytest.raises(InvalidEscapeError):
        tokenize(r"'\u{}'")
    with pytest.raises(InvalidEscapeError):
        tokenize(r"'\u{abcdefg}'")
    with pytest.raises(ParserError):
        tokenize('"unterminated')
    with pytest.raises(ParserError):
        tokenize('"unterminated escape \\')


def test_tokenize_binary_string() -> None:
    all_bytes = bytes(i for i in range(256))
    bstr = b"str\0\0\x01\0\0" + all_bytes
    assert tokenize(bstr) == [BinaryString(all_bytes, "p8scii")]
    with pytest.raises(InvalidBinaryStringError):
        tokenize(bstr[:-1])


def test_tokenize_ignores_whitespace() -> None:
    assert tokenize("") == []
    assert tokenize("\r\n\t ") == []
    assert tokenize("\r\n\t abc\r\n\t def\r\n\t ghi\r\n\t ") == [
        Identifier("abc"),
        Identifier("def"),
        Identifier("ghi"),
    ]


def test_tokenize_ignores_comments() -> None:
    assert tokenize("--") == []
    assert tokenize("-- Hello") == []
    assert tokenize("-- Hello\nHello") == [Identifier("Hello")]
    assert tokenize("--[[Hello\nHello]]Hello") == [Identifier("Hello")]


def test_tokenize_complex() -> None:
    pod = '{bmp=userdata("u8",16,16),flags=0,pan_x=0,pan_y=0,zoom=8}'
    assert tokenize(pod) == [
        LeftBrace(),
        Identifier("bmp"),
        Equals(),
        Identifier("userdata"),
        LeftParen(),
        String("u8"),
        Comma(),
        Number(16),
        Comma(),
        Number(16),
        RightParen(),
        Comma(),
        Identifier("flags"),
        Equals(),
        Number(0),
        Comma(),
        Identifier("pan_x"),
        Equals(),
        Number(0),
        Comma(),
        Identifier("pan_y"),
        Equals(),
        Number(0),
        Comma(),
        Identifier("zoom"),
        Equals(),
        Number(8),
        RightBrace(),
    ]


def test_tokenize_binary_userdata() -> None:
    pxu1 = b"pxu\0\x03\x10\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    assert tokenize(pxu1) == [BinaryUserdata(Userdata(DataType.U8, 10))]
    pxu2 = b"pxu\0\x03\x28\xe8\x03\x00\x00\x04\xf0\xff\xff\xff\xdb"
    assert tokenize(pxu2) == [BinaryUserdata(Userdata(DataType.U8, 1000))]
    pxu3 = b"pxu\0\x0c\x88\xe8\x03\x00\x00\x00\xff\x00\x00\xff\xff\xea"
    assert tokenize(pxu3) == [BinaryUserdata(Userdata(DataType.I16, 1000))]
    pxu4 = b"{d=pxu\0\x0c\x88\xe8\x03\x00\x00\x00\xff\x00\x00\xff\xff\xea}"
    assert tokenize(pxu4) == [
        LeftBrace(),
        Identifier("d"),
        Equals(),
        BinaryUserdata(Userdata(DataType.I16, 1000)),
        RightBrace(),
    ]
