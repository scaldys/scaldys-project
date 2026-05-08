.. _project_layout:

**************
Project Layout
**************

This page describes the directory structure your project must follow for
``scaldys-builder`` to work correctly, and documents where all build output
is written.  For how ``scaldys-builder`` locates the project root at runtime,
see :ref:`cli_usage`.

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
    │   ├── manual/                 ← Sphinx project (user guide)
    │   │   ├── source/
    │   │   │   ├── conf.py
    │   │   │   └── index.rst
    │   │   └── Makefile
    │   └── developer_guide/        ← Sphinx project (API docs, optional)
    │       └── source/
    │           └── conf.py
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

Every immediate subdirectory of ``docs/`` is treated as an independent
documentation unit.  The subdirectory names are freely choosable — there
are no fixed or required names.  ``scaldys-builder`` auto-detects the engine
used by each unit from its contents (see :ref:`documentation_building`).

Configure which units are included in the distribution and which need a
``sphinx-apidoc`` pre-pass via ``[docs]`` in ``builder.toml``::

    [docs]
    dist_dirs = ["manual"]
    apidoc_dirs = ["developer_guide"]

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
        <name>/                 ← one directory per docs/ subdirectory
            html/               ← multi-page HTML
            singlehtml/         ← single-page HTML
        pyinstaller/            ← PyInstaller work directory

For example, with ``docs/manual/`` and ``docs/developer_guide/``:

.. code-block:: text

    build/
        compiled/
        manual/
            html/
            singlehtml/
        developer_guide/
            html/
            singlehtml/
        pyinstaller/

``dist/`` — final artefacts
------------------------------

.. code-block:: text

    dist/
        pyinstaller/
            bin/                ← executable + libraries (from PyInstaller)
            documentation/
                <name>/         ← one directory per entry in dist_dirs
            examples/           ← example files (copied in, if examples/ exists)
            myapp_commandline.bat
            myapp_powershell.ps1
        setup/
            MyApp-Setup-1.2.3.exe   ← Windows installer (from Inno Setup)

For example, with ``dist_dirs = ["manual"]``:

.. code-block:: text

    dist/
        pyinstaller/
            bin/
            documentation/
                manual/         ← copied from build/manual/html/
            examples/
            myapp_commandline.bat
            myapp_powershell.ps1
        setup/
            MyApp-Setup-1.2.3.exe

Relationship between stages
============================

The three build stages consume each other's output:

.. code-block:: text

    [docs]  →  build/<name>/html/   (for each docs/ subdirectory)
                          ↓
    [exe]   →  dist/pyinstaller/bin/
                          ↓
    [installer]  →  copies build/<name>/html/ (for each dist_dirs entry)
                        + launchers + examples into dist/pyinstaller/
                     runs ISCC.exe → dist/setup/MyApp-Setup-x.y.z.exe

Running stages out of order is possible but the later stages depend on
earlier output.  Use ``build windows all`` to run them in the correct
sequence automatically.
