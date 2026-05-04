scaldys-builder
===============

A modular build system for Python projects targeting Windows.

``scaldys-builder`` automates the complete Windows distribution pipeline:

- Sphinx documentation (user guide + developer guide)
- Cython compilation (optional, per-project configuration)
- PyInstaller bundling into a standalone executable
- Inno Setup installer creation

Installation
------------

Install as a development dependency using uv::

    uv add --dev scaldys-builder

Install optional extras for the features you need::

    uv add --dev "scaldys-builder[cython,windows,docs]"

Usage
-----

Run the full build from your project root::

    scaldys-build build windows all

Individual steps::

    scaldys-build build windows docs
    scaldys-build build windows exe
    scaldys-build build windows installer
    scaldys-build build windows clean

Configuration
-------------

Create a ``builder.toml`` in your project root to configure project-specific
build settings.  If the file is absent, all defaults apply (pure-Python build,
packaging files expected at ``packaging/windows/``).

Example ``builder.toml``::

    [cython]
    compiled_modules = [
        "myapp.core.engine",    # performance-critical
        "myapp.core.crypto",    # obfuscation
    ]

    [windows]
    script_dir = "packaging/windows"  # location of .iss, .bat, .ps1, .ico

Windows packaging files
-----------------------

Place the following project-specific files in the directory specified by
``[windows] script_dir`` (default: ``packaging/windows/``)::

    packaging/windows/
        myapp.iss          # Inno Setup script
        myapp_commandline.bat
        myapp_powershell.ps1
        myapp.ico


Development
-----------

Setting up the development environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone the repository and create the virtual environment with uv::

    git clone <repository-url>
    cd scaldys-builder
    uv sync --group dev

This installs the package in editable mode along with all development
dependencies (pytest, ruff, pyright, Sphinx, etc.).

Running the tests
~~~~~~~~~~~~~~~~~

::

    uv run pytest

With coverage::

    uv run pytest --cov=scaldys_builder --cov-report=term-missing

Linting and type checking
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    uv run ruff check src tests
    uv run ruff format src tests
    uv run pyright

Versioning
~~~~~~~~~~

Version is declared in two places that must be kept in sync:

- ``pyproject.toml`` — ``[project] version``
- ``src/scaldys_builder/__init__.py`` — ``__version__``

Update both before tagging a release.

Building the package
~~~~~~~~~~~~~~~~~~~~

Build a source distribution and wheel::

    uv build

Outputs are written to ``dist/``.

Publishing to PyPI
~~~~~~~~~~~~~~~~~~

Publish using uv (requires a PyPI API token configured in your environment
or ``uv`` settings)::

    uv publish

To publish to TestPyPI first, uncomment the ``[[tool.uv.index]]`` block in
``pyproject.toml`` and run::

    uv publish --index testpypi

Consuming a local development version in another project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While iterating on the library, you can point a consuming project directly
at the local source tree without publishing::

    # From inside the consuming project
    uv add --dev "scaldys-builder @ path/to/scaldys-builder"

Or install in editable mode so changes in the library are reflected
immediately without reinstalling::

    uv add --dev --editable "path/to/scaldys-builder"
