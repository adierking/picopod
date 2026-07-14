import math
import re

import pytest

from picopod import p8scii
from picopod.pod import pod
from picopod.userdata import Compression, DataType, Userdata


def test_pod_number() -> None:
    assert pod(0) == b"0"
    assert pod(1234) == b"1234"
    assert pod(-1234) == b"-1234"
    assert pod(1234.5) == b"1234.5"
    assert pod(-1234.5) == b"-1234.5"
    assert re.fullmatch(r"1\.797693\d*e\+308", pod(math.nan).decode("p8scii"))
    assert re.fullmatch(r"1\.797693\d*e\+308", pod(math.inf).decode("p8scii"))
    assert re.fullmatch(r"-1\.797693\d*e\+308", pod(-math.inf).decode("p8scii"))


def test_pod_literal() -> None:
    assert pod(None) == b"nil"
    assert pod(False) == b"false"
    assert pod(True) == b"true"


def test_pod_string() -> None:
    assert pod("") == b'""'
    assert pod("Hello, world!") == b'"Hello, world!"'

    assert pod('""') == rb'"\"\""'
    assert pod("[]") == rb'"[\093"'
    assert pod("New\nline") == rb'"New\nline"'
    assert pod("Meow 🐱!") == rb'"Meow \130!"'

    assert pod(b"hello", binary=False) == b'"hello"'
    assert pod(b"hello", binary=True) == b"str\0\x05\0\0\0hello"
    assert pod(b"\x01\x02\x03\x04", binary=False) == rb'"\001\002\003\004"'
    assert pod(b"\x01\x02\x03\x04", binary=True) == b"str\0\x04\0\0\0\x01\x02\x03\x04"
    assert pod({"s": b"hello"}, binary=True) == b"{s=str\0\x05\0\0\0hello}"

    assert pod("æther", invalid_chars="replace") == b'"?ther"'
    assert pod("æther", invalid_chars="ignore") == b'"ther"'
    with pytest.raises(UnicodeEncodeError):
        pod("æther")

    # s = ""
    # for i = 0, 255 do
    #   s ..= chr(i)
    # end
    # set_clipboard(pod(s))
    all_characters = (
        rb"\000\001\002\003\004\005\006\007\008\009\n\011\012\013\014\015\016\017\018"
        rb"\019\020\021\022\023\024\025\026\027\028\029\030\031"
        rb" !\"#$%&'()*+,-./0123456789:;<=>?@"
        rb"ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\\093^_`abcdefghijklmnopqrstuvwxyz{|}~"
        rb"\127\128\129\130\131\132\133\134\135\136\137\138\139\140\141\142\143\144\145"
        rb"\146\147\148\149\150\151\152\153\154\155\156\157\158\159\160\161\162\163\164"
        rb"\165\166\167\168\169\170\171\172\173\174\175\176\177\178\179\180\181\182\183"
        rb"\184\185\186\187\188\189\190\191\192\193\194\195\196\197\198\199\200\201\202"
        rb"\203\204\205\206\207\208\209\210\211\212\213\214\215\216\217\218\219\220\221"
        rb"\222\223\224\225\226\227\228\229\230\231\232\233\234\235\236\237\238\239\240"
        rb"\241\242\243\244\245\246\247\248\249\250\251\252\253\254\255"
    )
    assert pod(p8scii.CHARACTERS) == b'"' + all_characters + b'"'


def test_pod_list() -> None:
    assert pod([]) == b"{}"
    assert pod([1]) == b"{1}"
    assert pod([1, 2, 3]) == b"{1,2,3}"
    assert pod([1, None, 3, None]) == b"{1,nil,3}"
    assert pod([[], []]) == b"{{},{}}"
    assert pod([[1], [2]]) == b"{{1},{2}}"
    assert pod([[1, 2, 3], [4, 5, 6]]) == b"{{1,2,3},{4,5,6}}"


def test_pod_dict() -> None:
    assert pod({}) == b"{}"
    assert pod({"x": 1}) == b"{x=1}"
    assert pod({"x": 1, "y": 2, "z": 3}) == b"{x=1,y=2,z=3}"
    assert pod({"x": None, "y": 2, "z": None}) == b"{y=2}"
    assert pod({"🐱": 1}) == rb'{["\130"]=1}'
    assert pod({"new\nline": 1}) == rb'{["new\nline"]=1}'
    assert pod({0: "a"}) == b'{[0]="a"}'
    assert pod({1: "a"}) == b'{"a"}'
    assert pod({2: "a"}) == b'{[2]="a"}'
    assert pod({1: "a", 2: "b", 3: "c"}) == b'{"a","b","c"}'
    assert pod({1: "a", 2: "b", 3: "c", 4: None}) == b'{"a","b","c"}'
    assert pod({1: "a", 2: None, 3: "c", 4: None}) == b'{"a",nil,"c"}'
    # TODO: Picotron emits `{[0]="a",[3]="c",[5]="d","b"}` for this
    assert (
        pod({0: "a", 1: "b", 2: None, 3: "c", 5: "d", 6: None})
        == b'{[0]="a",[5]="d","b",nil,"c"}'
    )


def test_pod_text_userdata() -> None:
    ud1 = Userdata(DataType.U8, data=list(range(16)))
    assert pod(ud1) == b'userdata("u8",16,"000102030405060708090a0b0c0d0e0f")'
    ud2 = Userdata(DataType.U8, 2, 8, list(range(16)))
    assert pod(ud2) == b'userdata("u8",2,8,"000102030405060708090a0b0c0d0e0f")'
    ud3 = Userdata(DataType.I16, data=[12345, 23456])
    assert pod(ud3) == b'userdata("i16",2,"30395ba0")'
    ud4 = Userdata(DataType.I32, data=[123456789])
    assert pod(ud4) == b'userdata("i32",1,"075bcd15")'
    ud5 = Userdata(DataType.F64, data=[0.5, 1.5])
    assert pod(ud5) == b'userdata("f64",2,"0.5,1.5")'


def test_pod_pxu_userdata() -> None:
    pxu1 = b"pxu\0\x03\x10\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    data1 = Userdata(DataType.U8, 10)
    assert pod(data1, binary=True, compression_hint=Compression.RAW) == pxu1

    pxu2 = b"pxu\0\x03\x28\xe8\x03\x00\x00\x04\xf0\xff\xff\xff\xdb"
    data2 = Userdata(DataType.U8, 1000)
    assert pod(data2, binary=True) == pxu2
    assert pod(data2, binary=True, compression_hint=Compression.MTF) == pxu2

    pxu3 = b"pxu\0\x03\x88\xe8\x03\x00\x00\x00\xff\x00\xff\xff\xea"
    assert pod(data2, binary=True, compression_hint=Compression.RLE) == pxu3

    pxu4 = b"pxu\0\x0c\x88\xe8\x03\x00\x00\x00\xff\x00\x00\xff\xff\xea"
    data4 = Userdata(DataType.I16, 1000)
    assert pod(data4, binary=True) == pxu4
    assert pod(data4, binary=True, compression_hint=Compression.MTF) == pxu4
    assert pod(data4, binary=True, compression_hint=Compression.RLE) == pxu4
    assert pod(data4, binary=True, compression_hint=Compression.RAW) == pxu4

    pxu5 = b"{d=pxu\0\x0c\x88\xe8\x03\x00\x00\x00\xff\x00\x00\xff\xff\xea}"
    data5 = Userdata(DataType.I16, 1000)
    assert pod({"d": data5}, binary=True) == pxu5


def test_pod_userdata_inf_nan() -> None:
    ud = Userdata(DataType.F64, 3, data=[math.inf, -math.inf, math.nan])
    assert pod(ud) == b'userdata("f64",3,"inf,-inf,nan")'


def test_pod_invalid_type() -> None:
    with pytest.raises(TypeError, match="set objects are not poddable"):
        pod(set())  # ty:ignore[invalid-argument-type]


def test_pod_base64() -> None:
    assert pod("Hello, world!", base64=True) == b"b64:IkhlbGxvLCB3b3JsZCEi"


def test_pod_lz4() -> None:
    assert (
        pod("A" * 1000, lz4=True)
        == b'lz4\x00\x0f\x00\x00\x00\xea\x03\x00\x00/"A\x01\x00\xff\xff\xff\xd3PAAAA"'
    )


def test_pod_lz4_base64() -> None:
    assert (
        pod("A" * 1000, lz4=True, base64=True)
        == b"b64:bHo0AA8AAADqAwAALyJBAQD----TUEFBQUEi"
    )
