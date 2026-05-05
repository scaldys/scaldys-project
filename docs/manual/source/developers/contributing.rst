.. _contributing:

************
Contributing
************

This guide covers how to set up a development environment for contributing to
``scaldys-builder`` itself: cloning, testing, linting, and publishing.

For extending ``scaldys-builder`` with new modules, build steps, or a new
platform builder, see :ref:`extension_points` instead.

.. contents:: On this page
   :local:
   :depth: 2


Development Setup
=================

Clone the repository and create the virtual environment with `uv
<https://docs.astral.sh/uv/>`_::

    git clone https://github.com/scaldys/scaldys-builder.git
    cd scaldys-builder
    uv sync --group dev

This installs the package in editable mode together with all development
dependencies (pytest, ruff, pyright, Sphinx, etc.).

Running the Tests
-----------------

::

    uv run pytest

With coverage::

    uv run pytest --cov=scaldys_builder --cov-report=term-missing

Linting and Type Checking
--------------------------

::

    uv run ruff check src tests
    uv run ruff format src tests
    uv run pyright

Building the Documentation Locally
------------------------------------

::

    uv run sphinx-build -b html docs/manual/source docs/manual/build/html

Or via the convenience wrapper::

    cd docs/manual && make html

Versioning, Building, and Publishing
--------------------------------------

Version is declared once in ``pyproject.toml`` under ``[project] version`` and
read at runtime via ``importlib.metadata`` in
``src/scaldys_builder/__about__.py``.  Update ``pyproject.toml`` before
tagging a release.

Build a wheel and source distribution::

    uv build

Publish to PyPI (requires a configured API token)::

    uv publish

To test against TestPyPI first, uncomment the ``[[tool.uv.index]]`` block in
``pyproject.toml`` and run::

    uv publish --index testpypi

Testing Changes Against a Consuming Project
--------------------------------------------

When developing a feature in ``scaldys-builder``, you can validate it against
a real consuming project without publishing to PyPI.  From inside the consuming
project, point it at your local ``scaldys-builder`` checkout::

    # From inside the consuming project
    uv add --dev "scaldys-builder @ path/to/scaldys-builder"

Or install in editable mode so any change to ``scaldys-builder`` source is
picked up immediately without reinstalling::

    uv add --dev --editable "path/to/scaldys-builder"


Reporting Issues
================

Please report bugs and feature requests on the GitHub issue tracker:

https://github.com/scaldys/scaldys-builder/issues
