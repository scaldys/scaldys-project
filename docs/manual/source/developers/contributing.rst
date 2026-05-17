.. _contributing:

************
Contributing
************

This guide covers how to set up a development environment for contributing to
``scaldys-project`` itself: cloning, testing, linting, and publishing.

For extending ``scaldys-project`` with new modules, build steps, or a new
platform builder, see :ref:`extension_points` instead.

.. contents:: On this page
   :local:
   :depth: 2


Development Setup
=================

Clone the repository and create the virtual environment with `uv
<https://docs.astral.sh/uv/>`_::

    git clone https://github.com/scaldys/scaldys-project.git
    cd scaldys-project
    uv sync --group dev

This installs the package in editable mode together with all development
dependencies (pytest, ruff, pyright, Sphinx, etc.).

Install the pre-commit hooks so they run automatically on every commit::

    uv run pre-commit install

Running the Tests
-----------------

Use the ``test`` command to run the full test suite the same way CI does::

    scaldys-project test

This is equivalent to::

    uv run pytest -v --durations=0 --cov --cov-report=xml

For a quicker local run with terminal coverage output::

    uv run pytest --cov=scaldys_project --cov-report=term-missing

Linting and Type Checking
--------------------------

Use the ``ci`` commands to run quality checks locally, mirroring the GitHub
Actions pipeline exactly::

    scaldys-project ci all          # run every step; stops on first failure
    scaldys-project ci lint         # ruff check only
    scaldys-project ci format       # ruff format --diff (check, no rewrite)
    scaldys-project ci typecheck    # pyright only
    scaldys-project ci build        # uv build only

Run these from the root of the ``scaldys-project`` repository.  If
``scaldys-project ci all`` passes, the GitHub Actions run will too.

The individual underlying commands are::

    uv run ruff check .
    uv run ruff format --diff .
    uv sync && uv run pyright ./src
    uv build

Markdown files are formatted with `Prettier <https://prettier.io/>`_ via
pre-commit.  To run it manually::

    uv run pre-commit run prettier --all-files

See :ref:`markdown_formatting_guide` for a full explanation of the
``.prettierrc`` options, why ``rbubley/mirrors-prettier`` is used, and how
CI enforces the same check.

Building the Documentation Locally
------------------------------------

::

    uv run sphinx-build -b html docs/manual/source docs/manual/build/html

Or via the convenience wrapper::

    cd docs/manual && make html

Versioning, Building, and Publishing
--------------------------------------

For the complete release procedure — PyPI Trusted Publishing setup, GitHub
environment configuration, workflow files, version bump, and TestPyPI dry run
— see :ref:`publishing`.

Quick reference for a local build::

    uv build

Testing Changes Against a Consuming Project
--------------------------------------------

When developing a feature in ``scaldys-project``, you can validate it against
a real consuming project without publishing to PyPI.  From inside the consuming
project, point it at your local ``scaldys-project`` checkout::

    # From inside the consuming project
    uv add --dev "scaldys-project @ path/to/scaldys-project"

Or install in editable mode so any change to ``scaldys-project`` source is
picked up immediately without reinstalling::

    uv add --dev --editable "path/to/scaldys-project"


Reporting Issues
================

Please report bugs and feature requests on the GitHub issue tracker:

https://github.com/scaldys/scaldys-project/issues
