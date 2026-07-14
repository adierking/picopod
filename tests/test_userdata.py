import copy
from array import array
from io import BytesIO
from pathlib import Path

import pytest

from picopod import PICOTRON_PALETTE
from picopod.errors import InvalidColorError, UnrecognizedTypeError
from picopod.userdata import Compression, DataType, Userdata

# The random-repeats tests here were generated with the following Lua code:
#
#   d = userdata("i16", 100, 100)
#   value, count = 0, 0
#   for y = 0, d:height() - 1 do
#       for x = 0, d:width() - 1 do
#           if count == 0 then
#               value = math.random(65536) - 1
#               count = math.random(100)
#           end
#           d:set(x, y, value)
#           count -= 1
#       end
#   end
#
# Replace `math.random(100)` with `1` to get the random-norepeats versions.


def _run_read_test(name: str, type: DataType, width: int, height: int) -> None:
    dir_path = Path(__file__).with_name("userdata")
    pxu_path = dir_path / f"{name}.pxu.bin"
    raw_path = dir_path / f"{name}.raw.bin"
    with raw_path.open("rb") as raw_file:
        raw = Userdata.read_raw(raw_file, type, width, height)
    with pxu_path.open("rb") as pxu_file:
        pxu = Userdata.read_pxu(pxu_file)
    assert raw == pxu


def _run_write_test(
    name: str,
    type: DataType,
    width: int,
    height: int,
) -> None:
    dir_path = Path(__file__).with_name("userdata")
    pxu_path = dir_path / f"{name}.pxu.bin"
    raw_path = dir_path / f"{name}.raw.bin"
    with raw_path.open("rb") as raw_file:
        raw = Userdata.read_raw(raw_file, type, width, height)
    with pxu_path.open("rb") as pxu_file:
        pxu_data = pxu_file.read()
    stream = BytesIO()
    raw.write_pxu(stream)
    assert len(stream.getvalue()) == len(pxu_data)
    assert stream.getvalue() == pxu_data


def test_userdata_operations() -> None:
    ud = Userdata(DataType.U8, 100, 100)

    assert ud.datatype == DataType.U8
    assert ud.width == 100
    assert ud.height == 100

    assert len(ud) == 100 * 100
    assert ud[:] == array("B", [0] * 100 * 100)

    assert all(ud[i] == 0 for i in range(100 * 100))
    assert ud[:10] == array("B", [0] * 10)
    assert len(list(ud)) == 100 * 100
    with memoryview(ud) as view:
        assert len(view) == 100 * 100

    ud2 = Userdata(DataType.U8, 100, 100)
    assert ud == ud2

    ud[0] = 1
    assert ud[0] == 1
    assert ud != ud2

    ud[1:5] = [2] * 4
    ud[5:10] = array("B", [2] * 5)
    assert list(ud[1:10]) == [2] * 9


def test_userdata_1d_vs_2d() -> None:
    ud1 = Userdata(DataType.U8, 100)
    ud2 = Userdata(DataType.U8, 100, 1)
    assert ud1 != ud2

    assert ud1.width == 100
    assert ud1.height is None

    assert ud2.width == 100
    assert ud2.height == 1


def test_userdata_shallow_copy() -> None:
    ud = Userdata(DataType.U8, 100, 100)
    ud2 = copy.copy(ud)
    assert ud2 == ud
    assert ud2 is not ud
    ud[0] = 1
    assert ud2[0] == 1


def test_userdata_deep_copy() -> None:
    ud = Userdata(DataType.U8, 100, 100)
    ud2 = copy.deepcopy(ud)
    assert ud2 == ud
    assert ud2 is not ud
    ud[0] = 1
    assert ud2[0] == 0


def test_userdata_type_strings() -> None:
    u8 = Userdata("u8", 100, 100)
    assert u8.datatype == DataType.U8
    assert str(u8.datatype) == "u8"

    i16 = Userdata("i16", 100, 100)
    assert i16.datatype == DataType.I16
    assert str(i16.datatype) == "i16"

    i32 = Userdata("i32", 100, 100)
    assert i32.datatype == DataType.I32
    assert str(i32.datatype) == "i32"

    i64 = Userdata("i64", 100, 100)
    assert i64.datatype == DataType.I64
    assert str(i64.datatype) == "i64"

    f64 = Userdata("f64", 100, 100)
    assert f64.datatype == DataType.F64
    assert str(f64.datatype) == "f64"

    with pytest.raises(UnrecognizedTypeError):
        _ = Userdata("foo", 100, 100)


def test_userdata_to_rgb() -> None:
    ud = Userdata("u8", data=list(range(32)))
    expected = b""
    for r, g, b in PICOTRON_PALETTE:
        expected += bytes([r, g, b])
    assert ud.to_rgb() == expected

    ud[0] = 32
    with pytest.raises(InvalidColorError):
        ud.to_rgb()


def test_userdata_from_rgb() -> None:
    rgb = bytearray()
    for r, g, b in PICOTRON_PALETTE:
        rgb.extend([r, g, b])
    ud = Userdata.from_rgb(8, 4, rgb)
    assert list(ud) == list(range(32))

    rgb[0] = 1
    with pytest.raises(InvalidColorError, match="not in the palette"):
        Userdata.from_rgb(8, 4, rgb)

    with pytest.raises(ValueError, match="width must"):
        Userdata.from_rgb(-16, 4, rgb)
    with pytest.raises(ValueError, match="height must"):
        Userdata.from_rgb(16, -4, rgb)
    with pytest.raises(ValueError, match="image data size"):
        Userdata.from_rgb(9, 7, rgb)
    with pytest.raises(ValueError, match="image data size"):
        Userdata.from_rgb(5, 13, rgb)

    with pytest.raises(InvalidColorError, match="Invalid color"):
        Userdata.from_rgb(1, 1, [256, 0, 0])
    with pytest.raises(InvalidColorError, match="Invalid color"):
        Userdata.from_rgb(1, 1, [-1, 0, 0])


def test_userdata_errors() -> None:
    with pytest.raises(ValueError, match="width must be positive"):
        Userdata("u8", 0)
    with pytest.raises(ValueError, match="width must be positive"):
        Userdata("u8", -1)
    with pytest.raises(ValueError, match="height must be positive"):
        Userdata("u8", 1, 0)
    with pytest.raises(ValueError, match="height must be positive"):
        Userdata("u8", 1, -1)
    with pytest.raises(ValueError, match="without a width or data"):
        # TODO: This should be made illegal with type annotations if it can be done
        # without being too complicated
        Userdata("u8")
    with pytest.raises(ValueError, match="Expected data with size"):
        Userdata("u8", 10, data=[0] * 9)
    with pytest.raises(ValueError, match="Expected data with size"):
        Userdata("u8", 10, data=[0] * 11)
    with pytest.raises(ValueError, match="Expected data with size"):
        Userdata("u8", 8, 8, data=[0] * 63)
    with pytest.raises(ValueError, match="Expected data with size"):
        Userdata("u8", 8, 8, data=[0] * 65)


def test_read_u8_raw_zero() -> None:
    buffer = b"pxu\0\x43\x10\x64\x64" + b"\0" * 10000
    pxu = Userdata.read_pxu(BytesIO(buffer))
    assert pxu == Userdata(DataType.U8, 100, 100)


def test_write_u8_raw_zero() -> None:
    userdata = Userdata(DataType.U8, 100, 100)
    stream = BytesIO()
    userdata.write_pxu(stream, Compression.RAW)
    assert stream.getvalue() == b"pxu\0\x43\x10\x64\x64" + b"\0" * 10000


def test_read_u8_mtf_zero() -> None:
    buffer = b"pxu\0" + b"".join(
        [
            b"\x43\x20\x64\x64\x04\xf0\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x27",
        ]
    )
    pxu = Userdata.read_pxu(BytesIO(buffer))
    assert pxu == Userdata(DataType.U8, 100, 100)


def test_write_u8_mtf_zero() -> None:
    userdata = Userdata(DataType.U8, 100, 100)
    stream = BytesIO()
    userdata.write_pxu(stream)
    expected = b"pxu\0" + b"".join(
        [
            b"\x43\x20\x64\x64\x04\xf0\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x27",
        ]
    )
    assert stream.getvalue() == expected


def test_read_u8_mtf_zero_large_width() -> None:
    buffer = b"pxu\0\x03\x28\x00\x01\x00\x00\x04\xf0\xf0"
    pxu = Userdata.read_pxu(BytesIO(buffer))
    assert pxu == Userdata(DataType.U8, 256)


def test_write_u8_mtf_zero_large_width() -> None:
    userdata = Userdata(DataType.U8, 256)
    stream = BytesIO()
    userdata.write_pxu(stream)
    expected = b"pxu\0\x03\x28\x00\x01\x00\x00\x04\xf0\xf0"
    assert stream.getvalue() == expected


def test_read_u8_mtf_zero_large_height() -> None:
    buffer = b"pxu\0\x43\x28\x01\x00\x00\x00\x00\x01\x00\x00\x04\xf0\xf0"
    pxu = Userdata.read_pxu(BytesIO(buffer))
    assert pxu == Userdata(DataType.U8, 1, 256)


def test_write_u8_mtf_zero_large_height() -> None:
    userdata = Userdata(DataType.U8, 1, 256)
    stream = BytesIO()
    userdata.write_pxu(stream)
    expected = b"pxu\0\x43\x28\x01\x00\x00\x00\x00\x01\x00\x00\x04\xf0\xf0"
    assert stream.getvalue() == expected


def test_read_u8_mtf_random_norepeats() -> None:
    _run_read_test("u8-mtf-random-norepeats", DataType.U8, 100, 100)


def test_write_u8_mtf_random_norepeats() -> None:
    _run_write_test("u8-mtf-random-norepeats", DataType.U8, 100, 100)


def test_read_u8_mtf_random_repeats() -> None:
    _run_read_test("u8-mtf-random-repeats", DataType.U8, 100, 100)


def test_write_u8_mtf_random_repeats() -> None:
    _run_write_test("u8-mtf-random-repeats", DataType.U8, 100, 100)


def test_read_u8_rle_zero() -> None:
    buffer = b"pxu\0" + b"".join(
        [
            b"\x43\x80\x64\x64\x00\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x36",
        ]
    )
    pxu = Userdata.read_pxu(BytesIO(buffer))
    assert pxu == Userdata(DataType.U8, 100, 100)


def test_write_u8_rle_zero() -> None:
    userdata = Userdata(DataType.U8, 100, 100)
    stream = BytesIO()
    userdata.write_pxu(stream, Compression.RLE)
    expected = b"pxu\0" + b"".join(
        [
            b"\x43\x80\x64\x64\x00\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x36",
        ]
    )
    assert stream.getvalue() == expected


def test_read_i16_rle_zero() -> None:
    buffer = b"pxu\0" + b"".join(
        [
            b"\x4c\x80\x64\x64\x00\xff\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x36",
        ]
    )
    pxu = Userdata.read_pxu(BytesIO(buffer))
    assert pxu == Userdata(DataType.I16, 100, 100)


def test_write_i16_rle_zero() -> None:
    userdata = Userdata(DataType.I16, 100, 100)
    stream = BytesIO()
    userdata.write_pxu(stream)
    expected = b"pxu\0" + b"".join(
        [
            b"\x4c\x80\x64\x64\x00\xff\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x36",
        ]
    )
    assert stream.getvalue() == expected


def test_read_i16_rle_random_norepeats() -> None:
    _run_read_test("i16-rle-random-norepeats", DataType.I16, 100, 100)


def test_write_i16_rle_random_norepeats() -> None:
    _run_write_test("i16-rle-random-norepeats", DataType.I16, 100, 100)


def test_read_i16_rle_random_repeats() -> None:
    _run_read_test("i16-rle-random-repeats", DataType.I16, 100, 100)


def test_write_i16_rle_random_repeats() -> None:
    _run_write_test("i16-rle-random-repeats", DataType.I16, 100, 100)
