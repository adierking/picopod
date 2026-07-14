Pod Formats
===========

Compression
-----------

Picopod supports LZ4-compressed and Base64-encoded pods. Note that the Base64 pod format is a
custom URL-safe variant that Picotron uses, not standard Base64.

To compress userdata, pass ``lz4=True`` to :func:`~picotron.pod()`:

.. testsetup:: *

   import re
   from picopod import pod, unpod

.. doctest::

   >>> pod("A" * 1000, lz4=True)
   b'lz4\x00\x0f\x00\x00\x00\xea\x03\x00\x00/"A\x01\x00\xff\xff\xff\xd3PAAAA"'

To Base64-encode userdata, pass ``base64=True``:

.. doctest::

   >>> pod("Hello, world!", base64=True)
   b'b64:IkhlbGxvLCB3b3JsZCEi'

You can even pass these options together:

.. doctest::

   >>> pod("A" * 1000, lz4=True, base64=True)
   b'b64:bHo0AA8AAADqAwAALyJBAQD----TUEFBQUEi'

Unpodding compressed and/or encoded data does not require any special flags because the format is
auto-detected:

.. doctest::

   >>> unpod("b64:IkhlbGxvLCB3b3JsZCEi")
   'Hello, world!'
   >>> len(unpod("b64:bHo0AA8AAADqAwAALyJBAQD----TUEFBQUEi"))
   1000

Metadata
--------

Some pods may have metadata at the beginning stored as a Lua block comment. This is automatically
ignored.

.. doctest::

   >>> unpod('--[[pod,created="2026-07-12 04:28:50",modified="2026-07-12 04:28:50",revision=0]]1234')
   1234

Picopod does not currently provide a built-in way to parse metadata, but you can do it yourself if
you use a regex to turn it into a table and then pass the result to :func:`~picopod.unpod`:

.. doctest::

   >>> p=b'--[[pod,created="2026-07-12 04:28:50",modified="2026-07-12 04:28:50",revision=0]]1234")'
   >>> unpod(b"{" + re.match(rb"^--\[\[(pod.*?)\]\]", p)[1] + b"}")
   {'created': '2026-07-12 04:28:50', 'modified': '2026-07-12 04:28:50', 'revision': 0}

This is safe because pods cannot contain the ``]]`` character sequence. It is always escaped:

.. doctest::

   >>> pod("]]")
   b'"\\093\\093"'

Nested Pods
-----------

Pods can actually contain calls to ``unpod()`` inside of them. Picotron generates these for Base64
pods if you call ``pod(..., 4)``, but it's accepted anywhere:

.. doctest::

   >>> unpod('unpod("b64:IkhlbGxvISI=")')
   'Hello!'
   >>> unpod('{1,unpod("2")}')
   [1, 2]

Byte Strings
------------

Picotron has an undocumented feature where passing 32 in ``pod()`` flags will emit strings in a raw
binary format. This is different from userdata and can be more compact for strings which contain a
large number of non-ASCII characters, since the characters don't have to be escaped.

Picopod supports these, and will generate them when you set ``binary=True`` and pass a ``bytes``
object. Otherwise ``bytes`` objects are coerced to strings to avoid confusion.

.. doctest::

   >>> pod(b"Hello")
   b'"Hello"'
   >>> pod(b"Hello", binary=True)
   b'str\x00\x05\x00\x00\x00Hello'