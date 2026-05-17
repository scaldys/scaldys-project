.. _overview:

********
Overview
********

What scaldys-project does for you
=================================

You write Python.  ``scaldys-project`` takes care of turning that code into
something you can hand to a Windows user.

Running a single command from your project root::

    scaldys-project build all

produces, in order:

1. **HTML documentation** — every documentation unit under ``docs/`` built
   to HTML, with configured units bundled into the installer for offline use.

2. **A Windows distribution** — the exact form depends on the
   ``deployment_mode`` you choose in ``scaldys.toml``:

   - **pyinstaller** (default): PyInstaller bundles the application into a
     self-contained directory that runs on any Windows machine without a
     Python installation.
   - **pyruntime**: a managed Python virtual environment is deployed
     alongside the application.  Use this when your app must coexist with
     Quarto, Jupyter, or another tool that requires a real Python interpreter.
   - **wheel_only**: only a binary distribution wheel is produced.  Use this
     for packages distributed via ``pip`` or ``uv``.

   In all modes, a ``.pyd``-only distribution wheel is built from compiled
   sources.  Optionally, selected modules are first compiled to native
   ``.pyd`` extensions with Cython for performance or to avoid shipping
   plain source code.

3. **A Windows installer** (``pyinstaller`` and ``pyruntime`` modes) — an
   Inno Setup ``.exe`` that installs the application, the documentation,
   launcher scripts, and example files; adds Start Menu and Desktop
   shortcuts; and handles uninstallation cleanly.

The end result is an ``artifacts/installer/`` folder containing a single
``setup.exe`` that you can ship directly to users, and a ``dist/``
folder with the distribution wheel.

The build pipeline at a glance
==============================

.. code-block:: text

    Your project
         │
         ▼
    ┌─────────────┐     Sphinx        ┌──────────────────────────┐
    │  docs/      │ ────────────────▶│ build/<name>/html/       │
    │  manual/    │                   └──────────────┬───────────┘
    │  dev_guide/ │                                  │
    └─────────────┘                                  │ public_doc_dirs → installer
    ┌─────────────┐   Cython (opt.)  ┌─────────────────────────────┐
    │  src/       │ ───────────────▶│ build/compiled/             │
    │  myapp/     │                  └───────────────┬─────────────┘
    └─────────────┘                                  │
                                                     │ Mode 1: PyInstaller
                                                     │ Mode 2: wheel + uv venv
                                                     │ Mode 3: wheel only
                                                     ▼
                                       ┌──────────────────────────────┐
                                       │ dist/                        │
                                       │   myapp-1.2.3-...win_amd64.whl │
                                       └──────────────────────────────┘
                                       ┌──────────────────────────────┐
                                       │ artifacts/portable/ (Mode 1&2)│
                                       │   bin/  ...  documentation/  │
                                       └──────────────┬───────────────┘
    ┌──────────────────┐  Inno Setup  (Mode 1 & 2)   │
    │ packaging/       │ ────────────────────────────▶
    │ windows/         │
    │   myapp.iss      │               ┌────────────────────────────┐
    └──────────────────┘               │ artifacts/installer/       │
                                       │   setup.exe                │
                                       └────────────────────────────┘

Getting started quickly with scaldys-template
=============================================

Setting up all the required files (Sphinx project, Inno Setup script,
launcher scripts, ``scaldys.toml``, ``pyproject.toml``, GitHub Actions
workflows, …) from scratch takes time.  `scaldys-template
<https://github.com/scaldys/scaldys-template>`_ is a ready-to-use project
template that already has everything wired together:

- A ``src``-layout Python package with a Typer-based CLI entry point
- ``scaldys.toml`` pre-configured with an example Cython module and
  ``deployment_mode = "pyinstaller"``
- ``packaging/windows/`` with a complete ``.iss`` script, auto-detecting
  launcher scripts, and an application icon
- ``docs/manual/`` with a working Sphinx project (freely renameable)
- ``pyproject.toml`` declaring ``scaldys-project[cython,windows,docs]`` as a
  dev dependency
- GitHub Actions workflows for CI, PyPI publishing, and release management

Clone or use it as a GitHub template to start a new project with the entire
Windows distribution pipeline already in place.

Where to go next
=================

**Starting a new project from scratch?**
    Use `scaldys-template <https://github.com/scaldys/scaldys-template>`_ — it
    comes with everything pre-wired.  Clone it and skip straight to
    :ref:`quickstart` to run your first build.

**Adding ``scaldys-project`` to an existing project?**
    Start with :ref:`installation` to add it as a dev dependency, then follow
    the :ref:`quickstart` to set up the required files and run your first build.

**Already set up and looking for reference information?**

- :ref:`cli_usage` — complete command reference
- :ref:`configuration` — ``scaldys.toml`` options
- :ref:`project_layout` — expected directory structure and build output
- :ref:`topics` — in-depth guides for each build step
