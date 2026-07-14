"""Picopod provides support for working with Picotron pods from Python."""

from . import p8scii
from .errors import Error, ParserError, UserdataError
from .palette import PICOTRON_PALETTE
from .pod import pod
from .unpod import unpod
from .userdata import Compression, DataType, Userdata

__all__ = [
    "PICOTRON_PALETTE",
    "Compression",
    "DataType",
    "Error",
    "ParserError",
    "Userdata",
    "UserdataError",
    "pod",
    "unpod",
]

p8scii.register()
