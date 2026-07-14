Type Safety
===========

:func:`~picopod.unpod()` can return values of many different types: :class:`int`, :class:`float`,
:class:`bool`, :class:`str`, :class:`bytes`, :class:`list`, :class:`dict`,
:class:`~picopod.Userdata`, or ``None``.

This can make life difficult for type checkers, and you often want to ensure that you get a specific
output type. You can do this by passing the ``type`` parameter to :func:`~picopod.pod`:

.. testsetup:: *

   from picopod import unpod

.. doctest::

   >>> unpod("1234", type=int)
   1234
   >>> unpod('1234', type=str)
   Traceback (most recent call last):
    ...
   TypeError: Expected str but got int

Additionally, to smooth out differences between Python and Lua, this will automatically convert
between some types if they don't immediately match:

.. doctest::

   >>> unpod("1234", type=float)
   1234.0
   >>> unpod("1234.5", type=int)
   1234
   >>> unpod("0", type=bool)
   False
   >>> unpod("true", type=int)
   1
   >>> unpod("{10,20,30}", type=dict)
   {1: 10, 2: 20, 3: 30}

Keep in mind that when working with arbitrary lists or dicts, you must still check the type of each
element you access, just like in Picotron. There is currently no support for any kind of schema
system for structured types.