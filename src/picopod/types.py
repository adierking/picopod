"""Type aliases for poddable types."""

from collections.abc import Buffer, Mapping, Sequence

from .userdata import Userdata

#: Primitive value types, which can also be used as table keys.
type Primitive = str | int | float | bool

#: A key-value table.
type DictTable = Mapping[Primitive, Value]

#: A table where all of the keys are numbers which increment starting from 1.
type ListTable = Sequence[Value]

#: Any table, which can be a list or a dict.
type Table = ListTable | DictTable

#: int or float userdata.
type AnyUserdata = Userdata[int] | Userdata[float]

#: Any type of poddable value.
type Value = Primitive | Buffer | Table | AnyUserdata | None
