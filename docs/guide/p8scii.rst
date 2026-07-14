P8SCII
======

Picopod automatically converts strings between UTF-8 and the Picotron character set ("P8SCII"):

.. testsetup:: *

   from picopod import pod, unpod

.. doctest::

   >>> pod("meow 🐱")
   b'"meow \\130"'
   >>> unpod(b'"meow \\130"')
   'meow 🐱'

This does mean that using characters outside P8SCII will throw an error:

.. doctest::

   >>> pod("æther")
   Traceback (most recent call last):
    ...
   UnicodeEncodeError: 'p8scii' codec can't encode character '\xe6' in position 0: No P8SCII equivalent

To ignore or replace errors, pass the ``invalid_chars`` option to :func:`~picopod.pod`:

.. doctest::

   >>> pod("æther", invalid_chars="replace")
   b'"?ther"'
   >>> pod("æther", invalid_chars="ignore")
   b'"ther"'

Importing Picopod will automatically register a ``p8scii`` codec with Python's encoding system, so
you can also use that to encode or decode strings yourself:

.. doctest::

   >>> "meow 🐱".encode("p8scii")
   b'meow \x82'
   >>> b'meow \x82'.decode("p8scii")
   'meow 🐱'

(Note: you can use :func:`picopod.p8scii.register` to explicitly register the codec if you're not
using anything else from Picopod.)

Finally, if you know what you're doing, you can pass a custom encoding to :func:`~picopod.pod` and
:func:`~picopod.unpod` if you want to disable P8SCII conversion. Be aware that Picotron will not be
able to display it by default.

.. doctest::

   >>> pod("æther", encoding="utf-8")
   b'"\\195\\166ther"'
   >>> unpod(b'"\\195\\166ther"', encoding="utf-8")
   'æther'