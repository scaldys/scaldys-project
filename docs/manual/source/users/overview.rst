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

1. **HTML documentation** — your Sphinx user guide compiled to a
   self-contained single-page HTML file, ready to be opened offline.
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
    │  docs/      │ ─────────────────▶│ build/manual/singlehtml/ │
    │  manual/    │                   └──────────────┬───────────┘
    └─────────────┘                                  │
                                                     │ copied into installer
    ┌─────────────┐   Cython (opt.)  ┌─────────────────────────────┐
    │  src/       │ ────────────────▶│ build/compiled/             │
    │  myapp/     │                  └───────────────┬─────────────┘
    └─────────────┘                                  │
                                                     │ PyInstaller
                                                     ▼
                                       ┌──────────────────────────┐
                                       │ dist/pyinstaller/bin/    │
                                       │   myapp.exe              │
                                       └───────────────┬──────────┘
                                                       │
    ┌──────────────────┐  Inno Setup                   │
    │ packaging/       │ ──────────────────────────────▶
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
- ``docs/manual/`` with a working Sphinx project
- ``pyproject.toml`` declaring ``scaldys-builder[cython,windows,docs]`` as a
  dev dependency
- GitHub Actions workflows for CI, PyPI publishing, and release management

Clone or use it as a GitHub template to start a new project with the entire
Windows distribution pipeline already in place.

Where to go next
=================

- :ref:`installation` — add ``scaldys-builder`` to an existing project
- :ref:`quickstart` — step-by-step first build walkthrough
- :ref:`cli_usage` — complete command reference
- :ref:`configuration` — ``builder.toml`` options
- :ref:`project_layout` — expected directory structure and build output
