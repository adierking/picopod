# Contributing to Picopod

## Guidelines

- No AI-generated code, documentation, issues, or comments will be accepted.

- All changes must be accompanied by unit tests and documentation where applicable.

- Make sure to run the linter and all unit tests before submitting a change (see below).

- Pull requests which make major changes will not be accepted unless you have discussed it with me
beforehand (e.g. on Discord or by opening an issue).

## Development Setup

Picopod uses [uv](https://docs.astral.sh/uv/) as its package manager. Make sure to install that
first.

To install dependencies and set up a Python environment, simply run:

```bash
uv sync
source .venv/bin/activate
```

## Running Tests

Before submitting changes, you must format, lint, typecheck, run the unit tests, and run
documentation tests.

```bash
ruff format
ruff check --fix
ty check
pytest
make -C docs doctest
```

## Documentation

Picopod uses [Sphinx](https://www.sphinx-doc.org/en/master/index.html) for documentation. The source
files are located in the docs/ directory.

The API reference is generated from docstrings using the autodoc extension. Picopod uses
[Google-style docstrings](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings).

To build the documentation locally, run

```bash
make -C docs html
```

Output will be in docs/_build/.
