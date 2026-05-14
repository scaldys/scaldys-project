.. _quickstart:

Quick Start
===========

This guide walks you through setting up an existing Python project to use
``scaldys-builder`` and running your first complete Windows build.

It assumes ``scaldys-builder`` is already installed in your project — if not,
see :ref:`installation` first.

Prerequisites
-------------

- ``scaldys-builder`` installed as a dev dependency (see :ref:`installation`)
- A Python project with a ``pyproject.toml`` at its root
- Windows (required for the build steps)
- Inno Setup installed — download from `jrsoftware.org
  <https://jrsoftware.org/isinfo.php>`_ and install to the default location

Step 1 — Create builder.toml
------------------------------

For a pure-Python project with packaging files in the default location
(``packaging/windows/``), no configuration file is needed — skip to Step 2.

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

Step 2 — Add Windows packaging files
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

See :ref:`windows_installer` for the expected content of each file, including
a minimal ``myapp.iss`` template.

Step 3 — Prepare your Sphinx documentation
--------------------------------------------

Create a subdirectory under ``docs/`` for each documentation unit.  The name
is freely choosable — ``manual``, ``help``, ``guide``, or anything else.
``scaldys-builder`` detects the engine automatically: a directory containing
``source/conf.py`` is treated as a Sphinx project.

If you do not already have a Sphinx project, create one from your project root
(replace ``manual`` with your chosen name)::

    sphinx-quickstart docs/manual

When prompted, choose **yes** to separate source and build directories.
This produces the ``docs/manual/source/`` layout that Sphinx requires.

To declare which documentation units should be bundled into the installer, add
to ``builder.toml``::

    [docs]
    dist_dirs = ["manual"]

See :ref:`documentation_building` for the complete expected layout, engine
auto-detection rules, and Sphinx configuration tips.

Step 4 — Run the full build
-----------------------------

From anywhere inside your project tree, run::

    scaldys-builder build windows all

``scaldys-builder`` walks up the directory tree to find ``pyproject.toml``
automatically — you do not need to ``cd`` to the project root first.

The command runs the following stages in order:

1. **docs** — Builds the Sphinx user guide and developer guide
2. **exe** — Optionally compiles modules with Cython, then bundles with PyInstaller
3. **installer** — Copies launcher scripts and HTML docs, then runs Inno Setup

A Rich progress bar tracks each stage. Output artefacts land in:

.. code-block:: text

    build/           ← intermediate artefacts
    dist/
        portable/bin/    ← standalone executable + libraries
        installer/          ← generated Windows installer (.exe)

Step 5 — Run individual stages
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
