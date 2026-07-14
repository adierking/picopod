import math

import pytest

from picopod.errors import EndOfStreamError, ParserError, UnexpectedTokenError
from picopod.unpod import unpod
from picopod.userdata import DataType, Userdata


def test_unpod_empty() -> None:
    with pytest.raises(EndOfStreamError):
        unpod("")
    with pytest.raises(EndOfStreamError):
        unpod("--pod")
    with pytest.raises(EndOfStreamError):
        unpod("--[[pod]]")


def test_unpod_none() -> None:
    assert unpod("nil") is None


def test_unpod_bool() -> None:
    assert bool(unpod("true")) is True
    assert bool(unpod("false")) is False


def test_unpod_number() -> None:
    # See test_tokenize_number() for a complete set of examples.
    assert unpod("1234") == 1234
    assert unpod("-1234") == -1234
    assert unpod("1234.5") == 1234.5
    assert unpod("-1234.5") == -1234.5
    assert unpod("1.25e1") == 12.5
    assert unpod("-1.25e1") == -12.5
    assert unpod("1.25e+1") == 12.5
    assert unpod("-1.25e+1") == -12.5
    assert unpod("1.25e-1") == 0.125
    assert unpod("-1.25e-1") == -0.125


def test_unpod_string() -> None:
    # See test_tokenize_string() for a complete set of examples.
    assert unpod("'hello'") == "hello"
    assert unpod('"hello"') == "hello"
    assert unpod(r"'\u{1f643}'", encoding="utf-8") == "\U0001f643"
    assert unpod(b"str\0\x05\0\0\0hello") == b"hello"


def test_unpod_table() -> None:
    assert unpod("{}") == []
    assert unpod("{nil}") == []
    assert unpod("{foo}") == []
    assert unpod("{nil,nil,nil}") == []
    assert unpod("{1}") == [1]
    assert unpod("{1,}") == [1]
    assert unpod("{1,nil}") == [1]
    assert unpod("{nil,1,nil,3,nil}") == [None, 1, None, 3]
    assert unpod("{foo,1,foo,3,foo}") == [1, 3]
    assert unpod("{10,20,30}") == [10, 20, 30]
    assert unpod("{10,20,30,}") == [10, 20, 30]
    assert unpod("{10 20 30}") == [10, 20, 30]  # yes, Picotron accepts this
    assert unpod("{10,20,30,nil}") == [10, 20, 30]
    assert unpod("{[1]=10,[2]=20,[3]=30}") == [10, 20, 30]
    assert unpod("{[1]=10,[2]=20,[3]=30,[4]=nil}") == [10, 20, 30]
    assert unpod("{[1]=10,[2]=20,[4]=30}") == {1: 10, 2: 20, 4: 30}
    assert unpod("{[0]=10,[1]=20,[2]=30}") == {0: 10, 1: 20, 2: 30}
    assert unpod("{'abc','def','ghi'}") == ["abc", "def", "ghi"]
    assert unpod("{x=10,y=20,z=30}") == {"x": 10, "y": 20, "z": 30}
    assert unpod("{['x']=10,['y']=20,['z']=30}") == {"x": 10, "y": 20, "z": 30}
    assert unpod("{[true]=10}") == {True: 10}
    assert unpod("{[true]=10,[false]=20}") == {True: 10, False: 20}
    assert unpod("{x=10,y=20,z=30,40}") == {"x": 10, "y": 20, "z": 30, 1: 40}
    assert unpod("{x=10,y=20,z=30,[1]=40,50}") == {"x": 10, "y": 20, "z": 30, 1: 50}
    assert unpod("{{1,2,3},{4,5,6}}") == [[1, 2, 3], [4, 5, 6]]
    assert unpod("{{}}") == [[]]
    assert unpod("{{},{},{}}") == [[], [], []]
    assert unpod("{{{{{{{{{{}}}}}}}}}}") == [[[[[[[[[[]]]]]]]]]]


def test_unpod_table_quirks() -> None:
    # TODO: Python treats bools as integers but Lua does not. Technically this should
    # unpod to {True: 10, 1: 20} but Python dicts don't support this because the keys
    # are considered equivalent. It may be possible to fix this with a custom dict type
    # or a custom bool type, but for now we document the behavior here as a quirk. This
    # should not be a problem for most pods.
    assert unpod("{[true]=10,[1]=20}") == {True: 20}


def test_unpod_userdata() -> None:
    assert unpod("userdata('u8',8,'0123456789abcdef')") == Userdata(
        DataType.U8, 8, data=bytes([0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF])
    )
    assert unpod("userdata('i16',1,'1234')") == Userdata(DataType.I16, 1, data=[0x1234])
    assert unpod("userdata('u16',1,'1234')") == Userdata(DataType.I16, 1, data=[0x1234])
    assert unpod("userdata('u32',1,'12345678')") == Userdata(
        DataType.I32, 1, data=[0x12345678]
    )
    assert unpod("userdata('i32',1,'12345678')") == Userdata(
        DataType.I32, 1, data=[0x12345678]
    )
    assert unpod("userdata('u64',1,'123456789abcdef0')") == Userdata(
        DataType.I64, 1, data=[0x123456789ABCDEF0]
    )
    assert unpod("userdata('i64',1,'123456789abcdef0')") == Userdata(
        DataType.I64, 1, data=[0x123456789ABCDEF0]
    )
    assert unpod("userdata('f64',3,'1.5,2.5,3.5')") == Userdata(
        DataType.F64, 3, data=[1.5, 2.5, 3.5]
    )
    pxu1 = b"pxu\0\x03\x10\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    assert unpod(pxu1) == Userdata(DataType.U8, 10)
    pxu2 = b"pxu\0\x03\x28\xe8\x03\x00\x00\x04\xf0\xff\xff\xff\xdb"
    assert unpod(pxu2) == Userdata(DataType.U8, 1000)
    pxu3 = b"pxu\0\x0c\x88\xe8\x03\x00\x00\x00\xff\x00\x00\xff\xff\xea"
    assert unpod(pxu3) == Userdata(DataType.I16, 1000)
    pxu4 = b"{d=pxu\0\x0c\x88\xe8\x03\x00\x00\x00\xff\x00\x00\xff\xff\xea}"
    assert unpod(pxu4) == {"d": Userdata(DataType.I16, 1000)}


def test_unpod_userdata_inf_nan() -> None:
    ud = unpod("userdata('f64',3,'inf,-inf,nan')", type=Userdata)
    assert ud[0] == math.inf
    assert ud[1] == -math.inf
    assert math.isnan(ud[2])


def test_unpod_type_constrained() -> None:
    assert unpod("false", type=bool) is False
    assert unpod("true", type=bool) is True

    assert unpod("0", type=int) == 0
    assert unpod("true", type=int) == 1
    assert unpod("1234", type=int) == 1234
    assert unpod("1234.5", type=int) == 1234

    assert unpod("true", type=float) == 1.0
    assert unpod("1234", type=float) == 1234.0
    assert unpod("1234.5", type=float) == 1234.5

    assert unpod("{1,2,3}", type=list) == [1, 2, 3]
    assert unpod("{10,20,30}", type=dict) == {1: 10, 2: 20, 3: 30}
    assert unpod("{10,nil,30}", type=dict) == {1: 10, 2: None, 3: 30}
    assert unpod("{10,20,nil}", type=dict) == {1: 10, 2: 20}
    assert unpod("{x=1,y=2,z=3}", type=dict) == {"x": 1, "y": 2, "z": 3}
    assert unpod("userdata('u8',1,'00')", type=Userdata) == Userdata(DataType.U8, 1)

    assert unpod("'hello'", type=str) == "hello"
    assert unpod("'hello'", type=bytes) == b"hello"
    assert unpod(b"str\0\x05\0\0\0hello", type=str) == "hello"
    assert unpod(b"str\0\x05\0\0\0hello", type=bytes) == b"hello"

    with pytest.raises(TypeError):
        unpod("1", type=str)
    with pytest.raises(TypeError):
        unpod("1.0", type=str)
    with pytest.raises(TypeError):
        unpod("true", type=str)
    with pytest.raises(TypeError):
        unpod("'0'", type=int)
    with pytest.raises(TypeError):
        unpod("'hello'", type=int)
    with pytest.raises(TypeError):
        unpod("{x=1,y=2,z=3}", type=list)
    with pytest.raises(TypeError):
        unpod("userdata('u8',5,'68656c6c6f')", type=str)


def test_unpod_comments() -> None:
    assert unpod("--pod\n1234") == 1234
    assert unpod("--[[pod]]\n1234") == 1234
    assert unpod(" --[[pod]] \n 1234 ") == 1234


def test_unpod_base64() -> None:
    assert unpod("b64:e3g9MSx5PTIsej0zfQ==") == {"x": 1, "y": 2, "z": 3}
    assert unpod("--[[pod]]b64:e3g9MSx5PTIsej0zfQ==") == {"x": 1, "y": 2, "z": 3}
    assert unpod("--[[pod]]\nb64:e3g9MSx5PTIsej0zfQ==") == {"x": 1, "y": 2, "z": 3}


def test_unpod_lz4() -> None:
    data = b"--[[pod]]" + bytes.fromhex(
        "6C7A34001F00000015010000"
        "FF0575736572646174612822"
        "7538222C3132382C22300100"
        "E9503030302229"
    )
    assert unpod(data) == Userdata(DataType.U8, 128)


def test_unpod_lz4_base64() -> None:
    pod = "--[[pod]]b64:bHo0AB8AAAAVAQAA/wV1c2VyZGF0YSgidTgiLDEyOCwiMAEA6VAwMDAiKQ=="
    assert unpod(pod) == Userdata(DataType.U8, 128)


def test_unpod_recursive() -> None:
    assert unpod("unpod('1')") == 1
    assert unpod(r"unpod('unpod(\'1\')')") == 1
    assert unpod("unpod('{x=1,y=2,z=3}')") == {"x": 1, "y": 2, "z": 3}
    assert unpod("unpod('b64:e3g9MSx5PTIsej0zfQ==')") == {"x": 1, "y": 2, "z": 3}
    with pytest.raises(ParserError, match="takes exactly one argument"):
        unpod("unpod()")
    with pytest.raises(ParserError, match="requires a string"):
        unpod("unpod(1)")
    with pytest.raises(ParserError, match="takes exactly one argument"):
        unpod("unpod('1',2)")


def test_unpod_errors() -> None:
    with pytest.raises(UnexpectedTokenError):
        unpod("foo")
    with pytest.raises(EndOfStreamError):
        unpod("{")
    with pytest.raises(EndOfStreamError):
        unpod("{1")
    with pytest.raises(EndOfStreamError):
        unpod("{1,")
    with pytest.raises(UnexpectedTokenError):
        unpod("{,}")
    with pytest.raises(UnexpectedTokenError):
        unpod("{1,,}")
    with pytest.raises(UnexpectedTokenError):
        unpod("{[}")
    with pytest.raises(UnexpectedTokenError):
        unpod("{[]}")
    with pytest.raises(UnexpectedTokenError):
        unpod("{[1]}")
    with pytest.raises(UnexpectedTokenError):
        unpod("{[1]=}")
    with pytest.raises(ParserError):
        unpod("{[{}]=1}")
    with pytest.raises(ParserError):
        unpod("{[nil]=1}")
    with pytest.raises(UnexpectedTokenError):
        unpod("{[1]=foo}")
    with pytest.raises(EndOfStreamError):
        unpod("{{{{{{{{{{}}}}}}}}}")
    with pytest.raises(ParserError):
        unpod('userdata("u8",-1,-1,"00")')
