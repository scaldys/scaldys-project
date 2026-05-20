.. _project_layout:

**************
Project Layout
**************

This page describes the directory structure your project must follow for
``scaldys-project`` to work correctly, and documents where all build output
is written.  For how ``scaldys-project`` locates the project root at runtime,
see :ref:`cli_usage`.

Project name and version
========================

``scaldys-project`` reads the project name and version from
``pyproject.toml``::

    [project]
    name = "myapp"
    version = "1.2.3"

These values are used:

- As the base name for PyInstaller artefacts (``myapp.exe``) in
  ``pyinstaller`` mode.
- As the base name when searching for packaging files in ``script_dir``
  (``myapp.iss``, ``myapp.ico``).
- As the version injected into the Inno Setup script
  (``/DMyAppVersion=1.2.3``).

Recommended directory layout
==============================

The following layout is the recommended structure for a project using
``scaldys-project``:

.. code-block:: text

    my-project/
    ├── pyproject.toml              ← project metadata (required)
    ├── scaldys-project.toml                ← scaldys-project config (optional)
    ├── .python-version             ← Python version pin (required for pyruntime mode)
    ├── src/
    │   └── myapp/                  ← Python source packages
    │       ├── __init__.py
    │       ├── __main__.py         ← application entry point (required)
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
    │       ├── myapp.iss           ← Inno Setup script (pyinstaller/pyruntime modes)
    │       ├── myapp_commandline.bat
    │       ├── myapp_powershell.ps1
    │       ├── setup_pyruntime.ps1 ← runtime setup script (pyruntime mode)
    │       └── myapp.ico
    ├── examples/                   ← example files (optional, bundled if present)
    └── tests/                      ← test suite (required)

In ``wheel_only`` mode the ``packaging/windows/`` directory and its
contents are not required.

Source layout (``src/`` layout)
---------------------------------

``scaldys-project`` defaults to ``source_root = "src"`` (configurable in
``scaldys-project.toml``).  If your project uses a flat layout (packages directly at
the project root), set::

    [cython]
    source_root = "."

Documentation layout
---------------------

Every immediate subdirectory of ``docs/`` is treated as an independent
documentation unit.  The subdirectory names are freely choosable — there
are no fixed or required names.  ``scaldys-project`` auto-detects the engine
used by each unit from its contents (see :ref:`documentation_building`).

Configure which units are included in the distribution via ``[docs]`` in
``scaldys-project.toml``::

    [docs]
    public_doc_dirs = ["manual"]

Windows packaging layout
--------------------------

The directory containing Windows packaging files defaults to
``packaging/windows/`` but can be changed via ``[windows] script_dir`` in
``scaldys-project.toml``::

    [windows]
    script_dir = "deploy/windows"

Examples directory
------------------

If an ``examples/`` directory exists in the project root,
``scaldys-project build windows`` copies its contents to
``artifacts/portable/examples/`` so the examples are included in the Windows
installer.  This directory is entirely optional.

Tests directory
---------------

A ``tests/`` directory at the project root is **required**.
``scaldys-project test`` runs ``pytest`` with ``testpaths = ["tests"]`` (set
in ``pyproject.toml``), so a missing directory would cause the test command
to silently collect nothing.  ``scaldys-project check`` enforces this rule
before any build starts (see :ref:`compliance_checking` — Rule 11).

Build output layout
===================

``scaldys-project`` writes all output under three top-level directories in the
project root.  All three are safe to delete (use ``build clean``).

``build/`` — intermediate artefacts
--------------------------------------

.. code-block:: text

    build/
        compiled/               ← staged source tree for Cython
        <name>/                 ← one directory per docs/ subdirectory
            html/               ← multi-page HTML
            singlehtml/         ← single-page HTML
        pyinstaller/            ← PyInstaller work directory (pyinstaller mode only)

``dist/`` — distribution wheel
--------------------------------

``dist/`` contains only the ``.whl`` file, following the PyPI convention
(``twine upload dist/*``, ``uv publish``).

.. code-block:: text

    dist/
        myapp-1.2.3-cp313-cp313-win_amd64.whl

``artifacts/`` — all other build outputs
------------------------------------------

``artifacts/`` holds every non-wheel output.  Its contents depend on the
active ``deployment_mode``.

**Mode 1: ``pyinstaller``**

.. code-block:: text

    artifacts/
        portable/
            bin/                ← executable + libraries (from PyInstaller)
                myapp.exe
                python313.dll
                _internal/
                myapp_commandline.bat
                myapp_powershell.ps1
            documentation/
                <name>/         ← one per entry in public_doc_dirs
            examples/           ← example files (if examples/ exists)
        documentation/
            <name>/             ← standalone docs copy, one per public_doc_dirs
        installer/
            setup.exe           ← Windows installer (from Inno Setup)

**Mode 2: ``pyruntime``**

.. code-block:: text

    artifacts/
        portable/
            bin/
                myapp_commandline.bat
                myapp_powershell.ps1
                setup_pyruntime.ps1
                uv.exe
                .python-version
            wheels/
                myapp-1.2.3-cp313-cp313-win_amd64.whl
            documentation/
                <name>/
            examples/
        documentation/
            <name>/
        pyruntime/              ← pre-built venv (offline mode only, bundle_pyruntime=true)
        installer/
            setup.exe

**Mode 3: ``wheel_only``**

.. code-block:: text

    artifacts/
        documentation/
            <name>/             ← only present if public_doc_dirs is non-empty

Relationship between stages
============================

The build steps consume each other's output:

.. code-block:: text

    [build docs]  →  build/<name>/html/   (for each docs/ subdirectory)
                              ↓
    [build windows]  →  Cython compilation → build/compiled/
                     →  wheel → dist/
                     →  Mode 1: PyInstaller → artifacts/portable/bin/
                     →  Mode 1/2: stages launchers, docs, examples into artifacts/portable/
                     →  Mode 1/2: Inno Setup → artifacts/installer/setup.exe

Running ``build all`` executes documentation and Windows distribution in
the correct sequence automatically.  Use ``build windows`` when the
documentation is already built and you only need to refresh the Windows
distribution artefacts.
