import pytest

from picopod import p8scii


def test_encode() -> None:
    assert p8scii.CHARACTERS.encode("p8scii") == bytes(range(256))


def test_decode() -> None:
    assert bytes(range(256)).decode("p8scii") == p8scii.CHARACTERS


def test_encode_errors() -> None:
    with pytest.raises(UnicodeError):
        "Meow 😻!".encode("p8scii", errors="strict")
    assert "Meow 😻!".encode("p8scii", errors="replace") == b"Meow ?!"
    assert "Meow 😻!".encode("p8scii", errors="ignore") == b"Meow !"
