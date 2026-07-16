# Picopod

🐍 [**PyPI**](https://pypi.org/project/picopod/) &nbsp;&nbsp;&nbsp;
📘 [**Documentation**](https://picopod.readthedocs.io/) &nbsp;&nbsp;&nbsp;
🧑‍🎓 [**Examples**](https://github.com/adierking/picopod/tree/main/examples) &nbsp;&nbsp;&nbsp;
🔧 [**Contributing**](https://github.com/adierking/picopod/blob/main/CONTRIBUTING.md)

Picopod is a Python library for working with [Picotron](https://www.lexaloffle.com/picotron.php)
pods, serialized objects which resemble Lua and also support embedded binary data. All pod features
as of Picotron 0.3.0d are supported, including userdata and compression.

It's useful for working with data files for Picotron programs and writing servers that efficiently
interact with Picotron clients. It is not a generic serialization library for arbitrary Python
objects.

Python 3.12 or above is required, and full type annotations for type checkers are included. The only
external dependency is the [`lz4`](https://pypi.org/project/lz4/) library needed to handle
compressed pods.

Make sure to read the [contribution guide](https://github.com/adierking/picopod/blob/main/CONTRIBUTING.md)
before submitting issues or pull requests.

## Basic Usage

You can install Picopod from PyPI using `pip` or another package manager:

```bash
pip install picopod
```

Then, use the `pod()` function to serialize values:

```python
>>> from picopod import pod
>>> pod(1234)
b'1234'
>>> pod("Hello, world!")
b'"Hello, world!"'
>>> pod([1, 2, 3])
b'{1,2,3}'
>>> pod({"fullscreen": False, "pixel_scale": 3})
b'{fullscreen=false,pixel_scale=3}'
```

And use `unpod()` to deserialize them:

```python
>>> from picopod import unpod
>>> unpod("1234")
1234
>>> unpod('"Hello, world!"')
'Hello, world!'
>>> unpod("{1,2,3}")
[1, 2, 3]
>>> unpod("{fullscreen=false,pixel_scale=3}")
{'fullscreen': False, 'pixel_scale': 3}
```

Refer to the [documentation](https://picopod.readthedocs.io/) for more details.

## License

Picopod is licensed under the terms of the [MIT license](LICENSE.txt).

Picopod is a community project. It is not affiliated with Lexaloffle.
