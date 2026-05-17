.. _quickstart:

Quick Start
===========

This guide walks you through setting up an existing Python project to use
``scaldys-project`` and running your first complete Windows build.

It assumes ``scaldys-project`` is already installed in your project — if not,
see :ref:`installation` first.

Prerequisites
-------------

- ``scaldys-project`` installed as a dev dependency (see :ref:`installation`)
- A Python project with a ``pyproject.toml`` at its root
- Windows (required for the build steps)
- Inno Setup installed (``pyinstaller`` and ``pyruntime`` modes only) — download
  from `jrsoftware.org <https://jrsoftware.org/isinfo.php>`_ and install to
  the default location

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
    deployment_mode = "pyinstaller"   # or "pyruntime" or "wheel_only"

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

In ``wheel_only`` mode these files are not required.

See :ref:`windows_installer` for the expected content of each file, including
a minimal ``myapp.iss`` template and auto-detecting launcher script examples.

Step 3 — Prepare your Sphinx documentation
--------------------------------------------

Create a subdirectory under ``docs/`` for each documentation unit.  The name
is freely choosable — ``manual``, ``help``, ``guide``, or anything else.
``scaldys-project`` detects the engine automatically: a directory containing
``source/conf.py`` is treated as a Sphinx project.

If you do not already have a Sphinx project, create one from your project root
(replace ``manual`` with your chosen name)::

    sphinx-quickstart docs/manual

When prompted, choose **yes** to separate source and build directories.
This produces the ``docs/manual/source/`` layout that Sphinx requires.

To declare which documentation units should be bundled into the installer, add
to ``builder.toml``::

    [docs]
    public_doc_dirs = ["manual"]

See :ref:`documentation_building` for the complete expected layout, engine
auto-detection rules, and Sphinx configuration tips.

Step 4 — Run the full build
-----------------------------

From anywhere inside your project tree, run::

    scaldys-project build all

``scaldys-project`` walks up the directory tree to find ``pyproject.toml``
automatically — you do not need to ``cd`` to the project root first.

The command runs the following stages in order:

1. **docs** — Builds the Sphinx documentation
2. **Cython compilation** (if configured) — compiles selected modules to ``.pyd``
3. **Windows distribution** — mode-dependent (PyInstaller or wheel build)
4. **installer** (``pyinstaller`` and ``pyruntime`` modes) — runs Inno Setup

A Rich progress bar tracks each stage. Output artefacts land in:

.. code-block:: text

    build/                ← intermediate artefacts
    dist/
        myapp-1.2.3-...whl    ← distribution wheel
    artifacts/
        portable/             ← staged distribution tree (pyinstaller/pyruntime modes)
        installer/            ← generated Windows installer (pyinstaller/pyruntime modes)
        documentation/        ← standalone docs copy (if public_doc_dirs is set)

Step 5 — Run individual stages
--------------------------------

You can run each stage independently:

.. code-block:: bash

    # Build documentation only
    scaldys-project build docs

    # Build Windows distribution only (mode-dependent, no docs rebuild)
    scaldys-project build windows

    # Remove build/, dist/ and artifacts/ directories
    scaldys-project build clean

All commands accept ``--verbose`` / ``-v`` for detailed debug output::

    scaldys-project build all --verbose

Next steps
----------

- :ref:`cli_usage` — complete command reference
- :ref:`configuration` — full ``builder.toml`` options
- :ref:`cython_compilation` — how Cython compilation works
- :ref:`windows_exe` — Windows deployment modes
- :ref:`windows_installer` — Inno Setup integration
