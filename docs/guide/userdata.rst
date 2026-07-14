Userdata
========

Picopod has full support for Picotron userdata objects, which store one-dimensional or
two-dimensional binary data.

Userdata Objects
----------------

You can work with userdata objects using the :class:`~picopod.Userdata` class::

   from picopod import Userdata

   u = Userdata("u8", 10)                  # 10 values (1D), zero-filled
   u = Userdata("u8", 5, 10)               # 5x10 (2D), zero-filled
   u = Userdata("u8", 2, 2, [1, 2, 3, 4])  # 2x2 (2D), initialized
   u = Userdata("u8", data=[1, 2, 3, 4])   # Automatic size, initialized

The userdata type can be a string like in Picotron, or you can also use the
:class:`~picopod.DataType` enum for something more strict::

    from picopod import Userdata, DataType

    u = Userdata("f64", data=[0.5, 1.0, 1.5, 2.0])
    u = Userdata(DataType.F64, data=[0.5, 1.0, 1.5, 2.0])

Userdata exposes :attr:`~picopod.Userdata.datatype`, :attr:`~picopod.Userdata.width`, and
:attr:`~picopod.Userdata.height` attributes:

.. testsetup:: *

   from picopod import pod, Userdata

.. doctest::

   >>> u = Userdata("u8", 5, 10)
   >>> u.datatype
   <DataType.U8: 1>
   >>> u.width
   5
   >>> u.height
   10

(Note that :attr:`~picopod.Userdata.height` for 1D userdata will be ``None``.)

It also supports slicing/indexing for accessing or mutating the data:

.. doctest::

   >>> u = Userdata("u8", data=[1, 2, 3, 4])
   >>> u[2]
   3
   >>> list(u[2:])
   [3, 4]
   >>> u[1] = 20
   >>> u[2:] = [30, 40]
   >>> list(u)
   [1, 20, 30, 40]

Note that for efficiency reasons, userdata is implemented using an ``array`` object. This means that
slicing userdata will alias it with a ``memoryview`` rather than copy it:

.. doctest::

   >>> u = Userdata("u8", data=[1, 2, 3, 4])
   >>> s = u[2:]
   >>> s
   <memory at ...>
   >>> u[2] = 30
   >>> list(s)
   [30, 4]

To copy a userdata object, use ``copy.deepcopy()``:

.. doctest::

   >>> import copy
   >>> u1 = Userdata("u8", data=[1, 2, 3, 4])
   >>> u2 = copy.deepcopy(u1)
   >>> u1[0] = 0
   >>> list(u1)
   [0, 2, 3, 4]
   >>> list(u2)
   [1, 2, 3, 4]

Binary Format
-------------

Picopod supports all of Picotron's userdata serialization formats, including binary ("PXU") data
with compression.

Like in Picotron, userdata serializes to a Lua function call by default:

.. doctest::

   >>> pod(Userdata("u8", data=[1, 2, 3, 4]))
   b'userdata("u8",4,"01020304")'

To emit binary data with an automatically-chosen compression format, call :func:`~picopod.pod` with
``binary=True``:

.. doctest::

   >>> pod(Userdata("u8", data=[1] * 1000), binary=True)
   b'pxu\x00\x03(\xe8\x03\x00\x00\x04\xf1\xff\xff\xff\xdb'

Binary format only supports 8-bit and 16-bit userdata. Attempting to use it with something else will
still just use text:

.. doctest::

   >>> pod(Userdata("f64", data=[1, 2, 3, 4]), binary=True)
   b'userdata("f64",4,"1.0,2.0,3.0,4.0")'

To select a particular compression algorithm (or none at all), call :func:`~picopod.pod` with a
``compression_hint``:

.. doctest::

   >>> from picopod import Compression
   >>> pod(Userdata("u8", data=[1, 2, 3, 4]), binary=True, compression_hint=Compression.RAW)
   b'pxu\x00\x03\x10\x04\x01\x02\x03\x04'
   >>> pod(Userdata("u8", data=[1, 2, 3, 4]), binary=True, compression_hint=Compression.RLE)
   b'pxu\x00\x03\x80\x04\x00\x00\x01\x00\x02\x00\x03\x00\x04'
   >>> pod(Userdata("u8", data=[1, 2, 3, 4]), binary=True, compression_hint=Compression.MTF)
   b'pxu\x00\x03 \x04\x04\x01\x02\x03\x04'

Image Data
----------

Userdata objects also have :meth:`~picopod.Userdata.to_rgb` and :meth:`~picopod.Userdata.from_rgb`
methods which convert palettized image data to/from RGB. You can use these along with a library like
Pillow::

   from PIL import Image

   # Unpod the input file, expecting 2D userdata.
   data = unpod(Path("image.pod").read_bytes(), type=Userdata)
   assert data.height is not None

   # Use to_rgb() to easily convert the userdata to RGB values.
   image = Image.frombytes("RGB", (data.width, data.height), data.to_rgb())

   # Convert and save to the output file.
   image.save("image.png")

Refer to the encode_image and decode_image examples for more.