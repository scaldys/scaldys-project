.. _cli_usage:

CLI Reference
=============

This page is a complete reference for every ``scaldys-project`` command and
option.  If you have not yet set up your project, start with :ref:`quickstart`.

``scaldys-project`` is invoked from the command line. All commands auto-discover
the project root by walking up the directory tree from the current working
directory until a ``pyproject.toml`` file is found.

Top-level usage::

    scaldys-project [OPTIONS] COMMAND [ARGS]...

Options
-------

.. option:: --help

   Show the help message and exit.  Available at every command level.

Command tree
------------

.. code-block:: text

    scaldys-project
    ├── init
    ├── check
    ├── test
    ├── publish
    ├── build
    │   ├── all
    │   ├── docs
    │   ├── windows
    │   └── clean
    ├── ci
    │   ├── all
    │   ├── lint
    │   ├── format
    │   ├── typecheck
    │   ├── markdown
    │   ├── doclint
    │   └── build
    └── format
        ├── all
        ├── python
        └── markdown

----

.. _cli_init:

``init``
---------

Scaffold a new scaldys-template-based project interactively.

.. code-block:: bash

    scaldys-project init [OPTIONS]

**What it does**

Launches an interactive wizard that collects project metadata (name, author,
description, deployment mode, and more), downloads
`scaldys-template <https://github.com/scaldys/scaldys-template>`_ from GitHub
(or uses a local copy), and produces a fully-substituted project directory
ready for development.

The wizard is divided into four sections:

1. **Project identity** — project name, package name, project slug,
   organisation name.
2. **Author & metadata** — author name and email, short description, initial
   version, optional GitHub username for README badge URLs.
3. **Build configuration** — Windows deployment mode
   (``pyinstaller`` / ``pyruntime`` / ``wheel_only``).
4. **Output & post-init actions** — target directory, whether to initialise
   a git repository, whether to run ``uv sync``.

A summary panel is shown before any files are written.  Confirm with **Y** to
proceed or **N** to abort.

After the project is created, use ``uv run`` to invoke ``scaldys-project``
commands inside the new project::

    cd my-cool-app
    uv run scaldys-project check

For the full guide including substitution details and post-init behaviour, see
:ref:`project_initialization`.

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--local PATH``
     - Use a local directory as the template source instead of downloading
       from GitHub.
   * - ``--template-ref REF``
     - Branch or tag of ``scaldys-template`` to download.  Default:
       ``main``.
   * - ``--force``, ``-f``
     - Overwrite the target directory if it already exists.
   * - ``--no-git``
     - Skip ``git init`` and the initial commit.
   * - ``--no-sync``
     - Skip running ``uv sync`` after project creation.
   * - ``--help``
     - Show command help and exit.

.. note::
   ``init`` does not require a ``pyproject.toml`` in the current directory.
   Unlike most other ``scaldys-project`` commands, it is run from the parent
   directory where you want the new project to appear, not from inside an
   existing project.

----

``check``
----------

Validate that the current project meets all scaldys-project requirements
without running any build step.

.. code-block:: bash

    scaldys-project check [OPTIONS]

**What it does**

Runs the full compliance check and reports any issues found.
Exits with code ``0`` if the project is compliant, or code ``1`` if any
requirement is not met.  This is identical to the automatic check that runs
at the start of ``build windows`` and ``build all``, but without triggering
a build.

The rules that are evaluated depend on the ``deployment_mode`` setting in
``scaldys-project.toml``.  In ``wheel_only`` mode the Inno Setup script and launcher
files are not required.

Use this command to verify a freshly cloned project, or to diagnose issues
after a compliance failure during a build.

For the complete list of rules and what each one requires, see
:ref:`compliance_checking`.

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--verbose``, ``-v``
     - Enable verbose (DEBUG-level) logging.
   * - ``--help``
     - Show command help and exit.

----

``test``
---------

Run the project test suite.

.. code-block:: bash

    scaldys-project test

**What it does**

Runs ``uv run pytest -v --durations=0 --cov --cov-report=xml`` in the current
working directory.  Exits with the same return code as pytest (``0`` on
success, non-zero on failure).

This command has no options; pass pytest arguments directly if you need custom
behaviour (e.g. ``uv run pytest -k my_test``).

----

``ci all``
-----------

Run every CI quality check in sequence, stopping on first failure.

.. code-block:: bash

    scaldys-project ci all

**What it does**

Executes the following steps in order, each mirroring the corresponding
GitHub Actions job step:

1. ``uv run ruff check .`` — Python lint
2. ``uv run ruff format --diff .`` — format check (no rewrite)
3. ``uv sync && uv run pyright ./src`` — Python type checking
4. ``uv run pre-commit run prettier --all-files`` (``--check`` mode, bundled config) — Markdown format check
5. ``uv run sphinx-lint docs/`` — RST documentation lint

If any step exits with a non-zero code the sequence stops immediately and
``scaldys-project`` exits with that code.

All ``ci`` commands operate on the **current working directory**, not the
project root discovered by ``pyproject.toml`` walk-up.  Run them from the
root of the project you want to check.

----

``ci lint``
------------

Run ruff in lint mode.

.. code-block:: bash

    scaldys-project ci lint

Executes ``uv run ruff check .`` in the current directory.  Exits with
ruff's return code.

----

``ci format``
--------------

Check code formatting without rewriting files.

.. code-block:: bash

    scaldys-project ci format

Executes ``uv run ruff format --diff .``.  Reports formatting differences
and exits non-zero if any file would be changed.  To actually reformat,
run ``uv run ruff format .`` directly.

----

``ci typecheck``
-----------------

Run pyright type checking.

.. code-block:: bash

    scaldys-project ci typecheck

Executes ``uv sync`` followed by ``uv run pyright ./src``.  The ``uv sync``
step ensures the virtual environment is up to date before pyright inspects
installed stubs.

----

``ci markdown``
-----------------

Check Markdown file formatting with Prettier.

.. code-block:: bash

    scaldys-project ci markdown

Runs Prettier via pre-commit in check-only mode (``--check``).  The
pre-commit configuration is bundled inside the ``scaldys-project`` wheel —
**no** ``.pre-commit-check-config.yaml`` file is required in your project.
Prettier reports which files would be reformatted and exits non-zero if any
file is not correctly formatted.  **No files are modified.**

This mirrors the *Prettier format* step in the GitHub Actions ``ci.yml``
workflow exactly.  To actually reformat Markdown files, use
``scaldys-project format markdown``.  See :ref:`markdown_formatting_guide`
for configuration details.

----

``ci doclint``
--------------

Check RST documentation files with sphinx-lint.

.. code-block:: bash

    scaldys-project ci doclint

Executes ``uv run sphinx-lint docs/`` in the current directory.  Reports RST
style and syntax issues and exits non-zero if any are found.  No files are
modified.

----

``ci build``
-------------

Build the project package.

.. code-block:: bash

    scaldys-project ci build

Executes ``uv build``.  Produces a wheel and sdist in ``dist/``.

----

``build all``
--------------

Run the complete end-to-end build workflow: documentation and Windows
distribution.

.. code-block:: bash

    scaldys-project build all [OPTIONS]

**What it does**

Runs compliance and pre-flight checks, then executes the following steps in
sequence, with a Rich progress bar tracking overall progress:

1. **Documentation** — builds every Sphinx unit under ``docs/``.
2. **Cython compilation** (if ``compiled_modules`` is non-empty) — compiles
   selected modules to ``.pyd`` extension files.
3. **Windows distribution** — mode-dependent (see ``build windows`` below).
4. **Packaging** — mode-dependent:

   - ``pyinstaller`` / ``pyruntime`` — stages artefacts and runs Inno Setup
     to produce a setup ``.exe`` in ``dist/installer/``.
   - ``wheel_only`` — copies each ``public_doc_dirs`` entry from
     ``build/<name>/html/`` to ``dist/documentation/<name>/``.

Any stage failure stops the build and reports the error.

Also performs a OneDrive synchronisation check at startup: if OneDrive is
actively syncing files in the project tree, a warning is displayed because
open file handles can cause intermittent failures during file operations.

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--verbose``, ``-v``
     - Enable verbose (DEBUG-level) logging.
   * - ``--help``
     - Show command help and exit.

----

``build docs``
---------------

Build the Sphinx documentation for the project.

.. code-block:: bash

    scaldys-project build docs [OPTIONS]

**What it does**

Scans every immediate subdirectory of ``docs/`` and builds each one as an
independent documentation unit.  The engine (Sphinx, MkDocs, …) is
auto-detected from each subdirectory's contents.

For each Sphinx unit (``source/conf.py`` present), two HTML formats are
produced: standard multi-page HTML and single-page HTML.

**Output locations**

.. code-block:: text

    build/<name>/html/          ← multi-page HTML
    build/<name>/singlehtml/    ← single-page HTML

where ``<name>`` is the subdirectory name (e.g. ``manual``,
``developer_guide``).

**Pre-flight requirement**: Sphinx (``sphinx-build``) must be installed.
Install it via the ``[docs]`` extra.

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--verbose``, ``-v``
     - Enable verbose (DEBUG-level) logging.
   * - ``--help``
     - Show command help and exit.

----

``build windows``
------------------

Build the Windows distribution for the project, without rebuilding
documentation.

.. code-block:: bash

    scaldys-project build windows [OPTIONS]

**What it does**

Reads ``deployment_mode`` from ``scaldys-project.toml`` (default: ``"wheel_only"``)
and runs the corresponding distribution pipeline:

``pyinstaller`` mode
    1. Cython compilation (if ``compiled_modules`` is non-empty).
    2. PyInstaller bundles the application into ``dist/portable/bin/``.
    3. Binary wheel built and placed in ``dist/wheels/``.
    4. Launcher scripts, documentation (from ``build/``), and examples are
       staged into ``dist/portable/``.
    5. Inno Setup produces a setup ``.exe`` in ``dist/installer/``.

``pyruntime`` mode
    1. Cython compilation (if ``compiled_modules`` is non-empty).
    2. Binary wheel built and placed in ``dist/wheels/``.
    3. Launcher scripts, documentation, examples, ``setup_pyruntime.ps1``,
       ``uv.exe``, and the wheel are staged into ``dist/portable/``.
    4. Optionally, a PythonRuntime venv is pre-built (``bundle_pyruntime =
       true``).
    5. Inno Setup produces a setup ``.exe`` in ``dist/installer/``.

``wheel_only`` mode
    1. Cython compilation (if ``compiled_modules`` is non-empty).
    2. Binary wheel built and placed in ``dist/wheels/``.
    No installer is created.

For full details on each mode see :ref:`windows_exe`.

**Pre-flight requirements**

- ``pyinstaller`` and ``pyruntime`` modes: Inno Setup (``ISCC.exe``) must be
  installed.
- ``pyinstaller`` mode: PyInstaller must be installed (via the ``[windows]``
  extra).

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--verbose``, ``-v``
     - Enable verbose (DEBUG-level) logging.
   * - ``--help``
     - Show command help and exit.

----

``build clean``
----------------

Remove all intermediate and final build artefacts.

.. code-block:: bash

    scaldys-project build clean [OPTIONS]

**What it does**

Deletes the ``build/`` and ``dist/`` directories in the project root.
Uses Windows-resilient retry logic to handle locked files.

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--verbose``, ``-v``
     - Enable verbose (DEBUG-level) logging.
   * - ``--help``
     - Show command help and exit.

----

``publish``
-----------

Publish the binary wheel from ``dist/`` to PyPI.

.. code-block:: bash

    scaldys-project publish [OPTIONS]

**What it does**

Locates the binary wheel produced by ``build all`` in the ``dist/``
directory and uploads it to PyPI using ``uv publish``.

Before uploading, the command performs the following safety checks in order:

1. **``dist/`` exists** — exits with code ``1`` if the directory is not found.
2. **Wheel present** — exits with code ``1`` if no ``.whl`` files are in ``dist/``.
3. **No pure-Python wheel** — if every wheel in ``dist/`` ends with
   ``-none-any.whl``, the upload is refused.  Publishing a pure wheel would
   expose Cython source code on PyPI.  Run ``scaldys-project build all`` first
   to produce a binary (platform-specific) wheel.
4. **Exactly one binary wheel** — if multiple binary wheels are present,
   the command exits with code ``1``.  Run ``scaldys-project build clean``
   followed by ``build all`` to obtain a clean single-wheel ``dist/``.

On success, ``uv publish <wheel>`` is invoked to upload the wheel.  The
``--test`` flag appends ``--index testpypi`` to the ``uv publish`` call,
redirecting the upload to Test PyPI.

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--test``
     - Publish to `Test PyPI <https://test.pypi.org>`_ instead of PyPI.
   * - ``--help``
     - Show command help and exit.

.. note::
   Run ``scaldys-project build all`` before publishing to ensure a fresh
   binary wheel exists in ``dist/``.  If stale wheels have accumulated,
   run ``scaldys-project build clean`` first.

----

``format all``
--------------

Auto-format all Python and Markdown files in sequence.

.. code-block:: bash

    scaldys-project format all

Runs ``format python`` followed by ``format markdown``, stopping on first
failure.  Use this as a quick pre-commit sweep to fix any formatting issues
before running ``ci all``.

----

``format python``
-----------------

Auto-format Python source files with ruff.

.. code-block:: bash

    scaldys-project format python

Executes ``uv run ruff format .``.  Rewrites any Python file whose
formatting differs from ruff's output.  Equivalent to ``ci format`` but
with the ``--diff`` flag removed so files are actually rewritten.

----

``format markdown``
-------------------

Auto-format Markdown files with prettier.

.. code-block:: bash

    scaldys-project format markdown

Executes ``uv run pre-commit run prettier --all-files``.  Prettier rewrites
any Markdown file that is not correctly formatted **in place**, then
pre-commit exits non-zero to signal that files were changed.  If all files
are already correctly formatted, the command exits with code ``0``.

Typical workflow after a ``ci markdown`` failure::

    scaldys-project format markdown
    git add -p
    git commit

See :ref:`markdown_formatting_guide` for configuration details.

----

Global behaviour
----------------

Project root discovery
^^^^^^^^^^^^^^^^^^^^^^

The ``build``, ``check``, and ``publish`` commands resolve the project root at
startup by walking up the directory tree from ``cwd`` until a
``pyproject.toml`` file is found.  You can invoke them from any subdirectory
of your project.

The ``ci`` and ``test`` commands operate directly on the **current working
directory** and do not perform project root discovery.  Run them from the root
of the project you want to check.

Logging
^^^^^^^

By default, ``INFO``-level messages are shown via Rich's formatted console
output.  Pass ``--verbose`` / ``-v`` to any command to enable ``DEBUG``-level
output, which includes all subprocess invocations and file operation details.

Exit codes
^^^^^^^^^^

``scaldys-project`` exits with code ``0`` on success and non-zero on failure.
Failures are always accompanied by a descriptive error message.
