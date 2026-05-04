.. _quickstart:

Quick Start
===========

This guide walks you through adding ``scaldys-builder`` to an existing Python
project and running your first complete Windows build in a few steps.

Prerequisites
-------------

- A Python project managed with ``pyproject.toml``
- ``uv`` installed
- Windows (for the build steps)

For a full list of external tool requirements, see :ref:`installation`.

Step 1 — Add scaldys-builder to your project
---------------------------------------------

From your project root, add ``scaldys-builder`` as a development dependency
with all build extras::

    uv add --dev "scaldys-builder[cython,windows,docs]"

If you do not need Cython compilation, omit that extra::

    uv add --dev "scaldys-builder[windows,docs]"

Step 2 — Create builder.toml (optional)
-----------------------------------------

For a pure-Python project with no Cython compilation and packaging files in
the default location (``packaging/windows/``), no configuration file is
needed — skip to Step 3.

For anything else, create ``builder.toml`` in your project root:

.. code-block:: toml

    [cython]
    compiled_modules = [
        "myapp.core.engine",
        "myapp.core.crypto",
    ]

    [windows]
    script_dir = "packaging/windows"

See :ref:`configuration` for the full configuration reference.

Step 3 — Add Windows packaging files
--------------------------------------

Create the directory specified by ``[windows] script_dir`` (default:
``packaging/windows/``) and place the following project-specific files
inside it:

.. code-block:: text

    packaging/windows/
        myapp.iss               # Inno Setup script
        myapp_commandline.bat   # Command-line launcher
        myapp_powershell.ps1    # PowerShell launcher
        myapp.ico               # Application icon (optional)

Replace ``myapp`` with your project name as declared in ``pyproject.toml``.

See :ref:`windows_installer` for Inno Setup script guidance.

Step 4 — Prepare your Sphinx documentation
--------------------------------------------

``scaldys-builder`` expects a Sphinx project under ``docs/manual/`` in your
project root. The documentation source must be at ``docs/manual/source/``.

If you do not already have a Sphinx project, create one::

    mkdir -p docs/manual
    sphinx-quickstart docs/manual

See :ref:`documentation_building` for the expected layout.

Step 5 — Run the full build
-----------------------------

From anywhere inside your project tree, run::

    scaldys-builder build windows all

``scaldys-builder`` walks up the directory tree to find ``pyproject.toml``
automatically, so you do not need to ``cd`` to the project root first.

The command runs the following stages in order:

1. **docs** — Builds the Sphinx user guide and developer guide
2. **exe** — Optionally compiles modules with Cython, then bundles with PyInstaller
3. **installer** — Copies launcher scripts and HTML docs, then runs Inno Setup

A Rich progress bar tracks each stage. Output artefacts land in:

.. code-block:: text

    build/           ← intermediate artefacts
    dist/
        pyinstaller/bin/    ← standalone executable + libraries
        setup/              ← generated Windows installer (.exe)

Step 6 — Run individual stages
--------------------------------

You can run each stage independently:

.. code-block:: bash

    # Build documentation only
    scaldys-builder build windows docs

    # Build the executable only (includes optional Cython compilation)
    scaldys-builder build windows exe

    # Build the installer only
    scaldys-builder build windows installer

    # Remove build/ and dist/ directories
    scaldys-builder build windows clean

All commands accept ``--verbose`` / ``-v`` for detailed debug output::

    scaldys-builder build windows all --verbose

Next steps
----------

- :ref:`cli_usage` — complete command reference
- :ref:`configuration` — full ``builder.toml`` options
- :ref:`cython_compilation` — how Cython compilation works
- :ref:`windows_exe` — PyInstaller bundling details
- :ref:`windows_installer` — Inno Setup integration
