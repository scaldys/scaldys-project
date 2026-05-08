.. _overview:

********
Overview
********

What scaldys-builder does for you
=================================

You write Python.  ``scaldys-builder`` takes care of turning that code into
something you can hand to a Windows user who has never installed Python.

Running a single command from your project root::

    scaldys-builder build windows all

produces, in order:

1. **HTML documentation** — every documentation unit under ``docs/`` built to
   HTML, with configured units bundled into the installer for offline use.
2. **A standalone executable** — your application bundled by PyInstaller
   into a folder that runs on any Windows machine without a Python
   installation.  Optionally, selected modules are first compiled to native
   ``.pyd`` extensions with Cython for performance or to avoid shipping
   plain source.
3. **A Windows installer** — an Inno Setup ``.exe`` that installs the
   executable, the documentation, launcher scripts, and example files; adds
   Start Menu and Desktop shortcuts; and handles uninstallation cleanly.

The end result is a ``dist/setup/`` folder containing a single
``MyApp-Setup-x.y.z.exe`` that you can ship directly to users.

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
    └─────────────┘                                  │ dist_dirs → installer
    ┌─────────────┐   Cython (opt.)  ┌─────────────────────────────┐
    │  src/       │ ───────────────▶│ build/compiled/             │
    │  myapp/     │                  └───────────────┬─────────────┘
    └─────────────┘                                  │
                                                     │ PyInstaller
                                                     ▼
                                       ┌──────────────────────────┐
                                       │ dist/pyinstaller/bin/    │
                                       │   myapp.exe              │
                                       └─────────────┬────────────┘
                                                     │
    ┌──────────────────┐  Inno Setup                 │
    │ packaging/       │ ────────────────────────────▶
    │ windows/         │
    │   myapp.iss      │               ┌────────────────────────────┐
    └──────────────────┘               │ dist/setup/                │
                                       │   MyApp-Setup-x.y.z.exe    │
                                       └────────────────────────────┘

Getting started quickly with scaldys-template
=============================================

Setting up all the required files (Sphinx project, Inno Setup script,
launcher scripts, ``builder.toml``, ``pyproject.toml``, GitHub Actions
workflows, …) from scratch takes time.  `scaldys-template
<https://github.com/scaldys/scaldys-template>`_ is a ready-to-use project
template that already has everything wired together:

- A ``src``-layout Python package with a Typer-based CLI entry point
- ``builder.toml`` pre-configured with an example Cython module
- ``packaging/windows/`` with a complete ``.iss`` script, launcher scripts,
  and an application icon
- ``docs/manual/`` with a working Sphinx project (freely renameable)
- ``pyproject.toml`` declaring ``scaldys-builder[cython,windows,docs]`` as a
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

**Adding ``scaldys-builder`` to an existing project?**
    Start with :ref:`installation` to add it as a dev dependency, then follow
    the :ref:`quickstart` to set up the required files and run your first build.

**Already set up and looking for reference information?**

- :ref:`cli_usage` — complete command reference
- :ref:`configuration` — ``builder.toml`` options
- :ref:`project_layout` — expected directory structure and build output
- :ref:`topics` — in-depth guides for each build step
