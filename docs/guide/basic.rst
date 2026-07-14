``pod()`` and ``unpod()``
=========================

Use the :func:`~picopod.pod()` function to serialize values:

.. doctest::

   >>> from picopod import pod
   >>> pod(1234)
   b'1234'
   >>> pod("Hello, world!")
   b'"Hello, world!"'
   >>> pod([1, 2, 3])
   b'{1,2,3}'
   >>> pod({"fullscreen": False, "pixel_scale": 3})
   b'{fullscreen=false,pixel_scale=3}'

And use :func:`~picopod.unpod()` to deserialize them:

.. doctest::

   >>> from picopod import unpod
   >>> unpod("1234")
   1234
   >>> unpod('"Hello, world!"')
   'Hello, world!'
   >>> unpod("{1,2,3}")
   [1, 2, 3]
   >>> unpod("{fullscreen=false,pixel_scale=3}")
   {'fullscreen': False, 'pixel_scale': 3}

:func:`~picopod.pod()` always returns bytes, but :func:`~picopod.unpod` can accept either bytes or a
string.

Error Handling
--------------

Unlike in Picotron, :func:`~picopod.unpod` does not return ``None`` if an error happens. Instead,
errors are raised using subclasses of :class:`~picopod.errors.Error`. For example,

.. testsetup:: *

   import picopod
   from picopod import unpod

.. testcode::

   try:
      unpod("foo")
   except picopod.Error as e:
      print(f"Error: {e}")

will print:

.. testoutput::

   Error: Unexpected token: 'foo'