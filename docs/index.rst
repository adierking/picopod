Picopod Documentation
=====================

Picopod is a Python library for working with `Picotron`_ pods, serialized objects which resemble Lua
and also support embedded binary data. All pod features as of Picotron 0.3.0d are supported,
including userdata and compression.

.. _Picotron: https://www.lexaloffle.com/picotron.php

It's mainly intended for writing servers that efficiently interact with Picotron clients and working
with data files for Picotron programs. It is not a generic serialization library for arbitrary
Python objects.

Python 3.12 or above is required, and full type annotations for type checkers are included. The only
external dependency is the `lz4`_ library needed to handle compressed pods.

.. _lz4: https://pypi.org/project/lz4/

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   guide/index
   reference/index