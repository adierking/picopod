from io import BytesIO

import pytest

from picopod._io import IOBytesExt


def test_read_u8() -> None:
    stream = IOBytesExt(BytesIO(b"\x01\x02\x03\x04\xff"))
    assert stream.read_u8() == 1
    assert stream.read_u8() == 2
    assert stream.read_u8() == 3
    assert stream.read_u8() == 4
    assert stream.read_u8() == 0xFF
    with pytest.raises(EOFError):
        stream.read_u8()


def test_read_i8() -> None:
    stream = IOBytesExt(BytesIO(b"\x01\x02\x03\x04\xff"))
    assert stream.read_i8() == 1
    assert stream.read_i8() == 2
    assert stream.read_i8() == 3
    assert stream.read_i8() == 4
    assert stream.read_i8() == -1
    with pytest.raises(EOFError):
        stream.read_i8()


def test_read_u16() -> None:
    stream = IOBytesExt(BytesIO(b"\x01\x02\xff\xfe\x00"))
    assert stream.read_u16_be() == 0x102
    assert stream.read_u16_be() == 0xFFFE
    with pytest.raises(EOFError):
        stream.read_u16_be()

    stream.seek(0)
    assert stream.read_u16_le() == 0x201
    assert stream.read_u16_le() == 0xFEFF
    with pytest.raises(EOFError):
        stream.read_u16_le()


def test_read_i16() -> None:
    stream = IOBytesExt(BytesIO(b"\x01\x02\xff\xfe\x00"))
    assert stream.read_i16_be() == 0x102
    assert stream.read_i16_be() == -0x2
    with pytest.raises(EOFError):
        stream.read_i16_be()

    stream.seek(0)
    assert stream.read_i16_le() == 0x201
    assert stream.read_i16_le() == -0x101
    with pytest.raises(EOFError):
        stream.read_i16_le()


def test_read_u32() -> None:
    stream = IOBytesExt(BytesIO(b"\x01\x02\x03\x04\xff\xff\xff\xfe\x00\x00\x00"))
    assert stream.read_u32_be() == 0x1020304
    assert stream.read_u32_be() == 0xFFFFFFFE
    with pytest.raises(EOFError):
        stream.read_u32_be()

    stream.seek(0)
    assert stream.read_u32_le() == 0x4030201
    assert stream.read_u32_le() == 0xFEFFFFFF
    with pytest.raises(EOFError):
        stream.read_u32_le()


def test_read_i32() -> None:
    stream = IOBytesExt(BytesIO(b"\x01\x02\x03\x04\xff\xff\xff\xfe\x00\x00\x00"))
    assert stream.read_i32_be() == 0x1020304
    assert stream.read_i32_be() == -0x2
    with pytest.raises(EOFError):
        stream.read_i32_be()

    stream.seek(0)
    assert stream.read_i32_le() == 0x4030201
    assert stream.read_i32_le() == -0x1000001
    with pytest.raises(EOFError):
        stream.read_i32_le()
