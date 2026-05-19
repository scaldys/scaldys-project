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

Linting, Type Checking, and Formatting
----------------------------------------

Use the ``ci`` commands to run all quality checks locally.  These are
**check-only**: they detect problems but never modify files, mirroring the
GitHub Actions pipeline exactly::

    scaldys-project ci all          # run every step; stops on first failure
    scaldys-project ci lint         # ruff check only
    scaldys-project ci format       # ruff format --diff (check, no rewrite)
    scaldys-project ci typecheck    # pyright only
    scaldys-project ci markdown     # prettier --check (check, no rewrite)

Run these from the root of the ``scaldys-project`` repository.  If
``scaldys-project ci all`` passes, the GitHub Actions run will too.

When a ``ci`` step reports failures, use the corresponding ``format`` command
to fix the files in place::

    scaldys-project format python   # rewrite Python files with ruff format
    scaldys-project format markdown # rewrite Markdown files with prettier
    scaldys-project format all      # rewrite both in sequence

After formatting, stage and commit the changes, then re-run ``ci all`` to
confirm everything is clean.

See :ref:`markdown_formatting_guide` for the full technical explanation of
how ``ci markdown`` and ``format markdown`` differ, how the pre-commit config
is split between a project-level file and the bundled wheel resource, and how
local behaviour compares to GitHub Actions.

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
