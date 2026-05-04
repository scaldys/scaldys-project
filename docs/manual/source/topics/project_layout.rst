.. _project_layout:

**************
Project Layout
**************

This topic explains the directory conventions that ``scaldys-builder``
expects in a consuming project and how it discovers the project root and
configuration at runtime.

Project root discovery
======================

Every ``scaldys-builder`` command locates the *project root* at startup by
walking up the directory tree from the current working directory until it
finds a directory containing a ``pyproject.toml`` file.  If no
``pyproject.toml`` is found, ``cwd`` is used as the fallback.

This means you can invoke ``scaldys-builder`` from any subdirectory of your
project — you do not need to ``cd`` to the root first::

    # All of these work from any subdirectory
    scaldys-builder build windows all
    scaldys-builder build windows docs

Project name and version
========================

``scaldys-builder`` reads the project name and version from
``pyproject.toml``::

    [project]
    name = "myapp"
    version = "1.2.3"

These values are used:

- As the base name for PyInstaller artefacts (``myapp.exe``).
- As the base name when searching for packaging files in ``script_dir``
  (``myapp.iss``, ``myapp.ico``).
- As the version injected into the Inno Setup script
  (``/DMyAppVersion=1.2.3``).

Recommended directory layout
==============================

The following layout is the recommended structure for a project using
``scaldys-builder``:

.. code-block:: text

    my-project/
    ├── pyproject.toml              ← project metadata (required)
    ├── builder.toml                ← scaldys-builder config (optional)
    ├── src/
    │   └── myapp/                  ← Python source packages
    │       ├── __init__.py
    │       └── core/
    │           ├── engine.py
    │           └── utils.py
    ├── docs/
    │   └── manual/                 ← Sphinx documentation project
    │       ├── source/
    │       │   ├── conf.py
    │       │   └── index.rst
    │       └── Makefile
    ├── packaging/
    │   └── windows/                ← Windows packaging files (default location)
    │       ├── myapp.iss
    │       ├── myapp_commandline.bat
    │       ├── myapp_powershell.ps1
    │       └── myapp.ico
    ├── examples/                   ← example files (optional, bundled if present)
    └── tests/

Source layout (``src/`` layout)
---------------------------------

``scaldys-builder`` defaults to ``source_root = "src"`` (configurable in
``builder.toml``).  If your project uses a flat layout (packages directly at
the project root), set::

    [cython]
    source_root = "."

Documentation layout
---------------------

The Sphinx documentation project must be at ``docs/manual/`` with source
files at ``docs/manual/source/``.  This path is not currently configurable.

Windows packaging layout
--------------------------

The directory containing Windows packaging files defaults to
``packaging/windows/`` but can be changed via ``[windows] script_dir`` in
``builder.toml``::

    [windows]
    script_dir = "deploy/windows"

Examples directory
------------------

If an ``examples/`` directory exists in the project root,
``scaldys-builder build windows installer`` copies its contents to
``dist/pyinstaller/examples/`` so the examples are included in the Windows
installer.  This directory is entirely optional.

Build output layout
===================

``scaldys-builder`` writes all output under two top-level directories in the
project root.  Both are safe to delete (use ``build windows clean``).

``build/`` — intermediate artefacts
--------------------------------------

.. code-block:: text

    build/
        compiled/               ← staged source tree for Cython + PyInstaller
        manual/
            html/               ← user guide (multi-page HTML)
            singlehtml/         ← user guide (single-page HTML)
        developer_guide/
            html/               ← developer / API guide (multi-page HTML)
        pyinstaller/            ← PyInstaller work directory

``dist/`` — final artefacts
------------------------------

.. code-block:: text

    dist/
        pyinstaller/
            bin/                ← executable + libraries (from PyInstaller)
            docs/               ← single-page HTML documentation (copied in)
            examples/           ← example files (copied in, if examples/ exists)
            myapp_commandline.bat
            myapp_powershell.ps1
        setup/
            MyApp-Setup-1.2.3.exe   ← Windows installer (from Inno Setup)

Relationship between stages
============================

The three build stages consume each other's output:

.. code-block:: text

    [docs]  →  build/manual/singlehtml/
                          ↓
    [exe]   →  dist/pyinstaller/bin/
                          ↓
    [installer]  →  copies singlehtml + launchers + examples
                        into dist/pyinstaller/
                     runs ISCC.exe → dist/setup/MyApp-Setup-x.y.z.exe

Running stages out of order is possible but the later stages depend on
earlier output.  Use ``build windows all`` to run them in the correct
sequence automatically.
