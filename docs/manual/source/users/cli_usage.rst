.. _cli_usage:

CLI Reference
=============

This page is a complete reference for every ``scaldys-project`` command and
option.  If you have not yet set up your project, start with :ref:`quickstart`.

``scaldys-project`` is invoked from the command line. All commands auto-discover
the project root by walking up the directory tree from the current working
directory until a ``pyproject.toml`` file is found.

In a uv workspace, ``build``, ``check``, ``test`` and ``publish`` also accept
``--package NAME`` / ``-p NAME`` (repeatable) and ``--all-packages`` to choose
the members to act on, and ``ci`` / ``format`` run at the workspace root.
See :ref:`uv_workspaces`.

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
    │   └── doclint
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
``scaldys-project.toml``.  In ``wheel_only`` mode the Inno Setup script,
the launcher files and ``__main__.py`` are not required.  For a uv
workspace member the version constraints on its internal dependencies are
checked as well.

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
   * - ``--package``, ``-p NAME``
     - uv workspace only: check this member (repeatable).  See
       :ref:`cli_targets`.
   * - ``--all-packages``
     - uv workspace only: check every member, libraries first.
   * - ``--help``
     - Show command help and exit.

----

``test``
---------

Run the project test suite.

.. code-block:: bash

    scaldys-project test [OPTIONS]

**What it does**

Runs ``uv run pytest -v --durations=0 --cov --cov-report=xml`` in the current
working directory. The complete command syntax is displayed in the terminal
output before execution. Exits with the same return code as pytest (``0`` on
success, non-zero on failure).

In a uv workspace, each selected member runs its own tests in its own
environment, from the workspace root::

    uv run --package <member> pytest <member>/tests -v --durations=0 --cov --cov-report=xml

At a virtual workspace root with no member selected, ``uv run pytest ...``
runs once at the root, using the root ``[tool.pytest.ini_options]
testpaths``.

Pass pytest arguments directly if you need custom behaviour
(e.g. ``uv run pytest -k my_test``).

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--package``, ``-p NAME``
     - uv workspace only: test this member (repeatable).  See
       :ref:`cli_targets`.
   * - ``--all-packages``
     - uv workspace only: test every member, libraries first.
   * - ``--help``
     - Show command help and exit.

----

``ci all``
-----------

Run every CI quality check in sequence, continuing regardless of errors.

.. code-block:: bash

    scaldys-project ci all

**What it does**

Executes the following steps in order, each mirroring the corresponding
GitHub Actions job step. The syntax for each underlying command is displayed
in the terminal output:

1. ``uv run ruff check .`` — Python lint
2. ``uv run ruff format --diff .`` — format check (no rewrite)
3. ``uv sync && uv run pyright ./src ./tests`` — Python type checking
4. ``uv run mdformat --check <targets>`` — Markdown format check
5. ``uv run sphinx-lint docs/`` — RST documentation lint

If any step fails, the command continues to the next one. After all steps have
been attempted, ``scaldys-project`` exits with code ``1`` if any failure
occurred, and displays a summary of the failed steps.

All ``ci`` commands run at the **project root**, found by walking up from
the current directory to the first ``pyproject.toml``, so they give the same
result from any subfolder.  In a uv workspace they run once at the
**workspace root**, also when started inside a member; the typecheck and
doclint steps then cover every member (see ``ci typecheck`` and
``ci doclint`` below).

----

``ci lint``
------------

Run ruff in lint mode.

.. code-block:: bash

    scaldys-project ci lint

Executes ``uv run ruff check .`` at the project (or workspace) root.  Exits
with ruff's return code.

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

Executes ``uv sync`` followed by ``uv run pyright ./src ./tests``.  The
``uv sync`` step ensures the virtual environment is up to date before
pyright inspects installed stubs.

In a uv workspace it runs ``uv sync --all-packages`` instead (a bare
``uv sync`` in a member would uninstall the other members).  Then:

- if the root ``pyproject.toml`` has a ``[tool.pyright]`` table, it runs
  ``uv run pyright`` without paths, so that table's ``include`` decides
  what is checked;
- otherwise it passes every member's source root and ``tests/`` folder, for
  example ``uv run pyright packages/app/src packages/app/tests ...``.

----

``ci markdown``
-----------------

Check Markdown file formatting with mdformat.

.. code-block:: bash

    scaldys-project ci markdown

Runs mdformat in check-only mode (``--check``) on discovered target Markdown
files (``README.md`` and any MkDocs documentation files in ``docs/``).
mdformat reports which files need formatting and exits non-zero if any file is
not correctly formatted.  **No files are modified.**

This mirrors the *Markdown format check* step in the GitHub Actions ``ci.yml``
workflow exactly.  The targets come from ``[format]`` in the root
``scaldys-project.toml``, and a warning is shown when they differ from the
``mdformat`` arguments in ``.github/workflows/ci.yml`` at the project (or
workspace) root.  To actually reformat Markdown files, use
``scaldys-project format markdown``.  See :ref:`markdown_formatting_guide`
for details.

----

``ci doclint``
--------------

Check RST documentation files with sphinx-lint.

.. code-block:: bash

    scaldys-project ci doclint

Executes ``uv run sphinx-lint docs/`` at the project root.  Reports RST
style and syntax issues and exits non-zero if any are found.  No files are
modified.

In a uv workspace it lints the root ``docs/`` (if present) and the
``docs/`` folder of every member in one call, for example
``uv run sphinx-lint docs/ packages/app/docs/``.

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

1. **Documentation** — builds every Sphinx unit under ``docs/``.  Skipped
   with an info message when the project has no ``docs/`` folder.
2. **Internal dependencies** (uv workspace apps only) — builds the wheels of
   the workspace members the app depends on into ``build/internal_wheels/``
   (see ``build windows`` below).
3. **Cython compilation** (if ``compiled_modules`` is non-empty) — compiles
   selected modules to ``.pyd`` extension files.
4. **Windows distribution** — mode-dependent (see ``build windows`` below).
5. **Packaging** — mode-dependent:

   - ``pyinstaller`` / ``pyruntime`` — stages artefacts and runs Inno Setup
     to produce a setup ``.exe`` in ``artifacts/installer/``.
   - ``wheel_only`` — copies each ``public_doc_dirs`` entry from
     ``build/<name>/html/`` to ``artifacts/documentation/<name>/``.

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
   * - ``--package``, ``-p NAME``
     - uv workspace only: act on this member (repeatable).  See
       :ref:`cli_targets`.
   * - ``--all-packages``
     - uv workspace only: act on every member, libraries first.
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
   * - ``--package``, ``-p NAME``
     - uv workspace only: act on this member (repeatable).  See
       :ref:`cli_targets`.
   * - ``--all-packages``
     - uv workspace only: act on every member, libraries first.
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
    2. PyInstaller bundles the application into ``artifacts/portable/bin/``.
    3. Binary wheel built and placed in ``dist/``.
    4. Launcher scripts, documentation (from ``build/``), and examples are
       staged into ``artifacts/portable/``.
    5. Inno Setup produces a setup ``.exe`` in ``artifacts/installer/``.

``pyruntime`` mode
    1. Cython compilation (if ``compiled_modules`` is non-empty).
    2. Binary wheel built and placed in ``dist/``.
    3. Launcher scripts, documentation, examples, ``setup_pyruntime.ps1``,
       ``uv.exe``, and the wheel are staged into ``artifacts/portable/``.
    4. Optionally (``bundle_pyruntime = true``), a PythonRuntime venv is
       pre-built at ``artifacts/pyruntime/`` with the project's own wheel
       (and its dependencies) and ``pyyaml`` installed into it.
    5. Inno Setup produces a setup ``.exe`` in ``artifacts/installer/``.

``wheel_only`` mode
    1. Cython compilation (if ``compiled_modules`` is non-empty).
    2. Binary wheel built and placed in ``dist/``.

    No installer is created.

For full details on each mode see :ref:`windows_exe`.

**uv workspace apps**: in ``pyinstaller`` and ``pyruntime`` mode, an app
member that depends on other workspace members first builds their wheels
(each member once per command run) into ``build/internal_wheels/``.  In
``pyinstaller`` mode PyInstaller then bundles them (``--paths``,
``--collect-submodules``, ``--copy-metadata``, their ``packaging/hooks``);
in ``pyruntime`` mode they are staged into ``artifacts/portable/wheels/``
and the offline PythonRuntime install finds them with ``--find-links``.
See :ref:`uv_workspaces`.

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
   * - ``--package``, ``-p NAME``
     - uv workspace only: act on this member (repeatable).  See
       :ref:`cli_targets`.
   * - ``--all-packages``
     - uv workspace only: act on every member, libraries first.
   * - ``--help``
     - Show command help and exit.

----

``build clean``
----------------

Remove all intermediate and final build artefacts.

.. code-block:: bash

    scaldys-project build clean [OPTIONS]

**What it does**

Empties the ``build/``, ``dist/`` and ``artifacts/`` directories in the
project root (in a uv workspace: in each selected member).  Uses
Windows-resilient retry logic to handle locked files.

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--verbose``, ``-v``
     - Enable verbose (DEBUG-level) logging.
   * - ``--package``, ``-p NAME``
     - uv workspace only: act on this member (repeatable).  See
       :ref:`cli_targets`.
   * - ``--all-packages``
     - uv workspace only: act on every member, libraries first.
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

In a uv workspace the checks above apply to each selected member's own
``dist/``.  Members are published libraries first, so a library reaches the
index before the apps that require it.  Members with the
``Private :: Do Not Upload`` classifier are skipped with a notice.  The
wheels of internal dependencies collected in ``build/internal_wheels/`` are
never published from the app.

**Options**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--test``
     - Publish to `Test PyPI <https://test.pypi.org>`_ instead of PyPI.
   * - ``--package``, ``-p NAME``
     - uv workspace only: publish this member (repeatable).  See
       :ref:`cli_targets`.
   * - ``--all-packages``
     - uv workspace only: publish every member, libraries first.
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

Runs ``format python`` followed by ``format markdown``, continuing regardless
of errors.  Use this as a quick formatting sweep to fix any issues before
running ``ci all``.  If any step fails, a summary is displayed and the
command exits non-zero.

----

``format python``
-----------------

Auto-format Python source files with ruff.

.. code-block:: bash

    scaldys-project format python

Executes ``uv run ruff format .`` at the project (or workspace) root.
Rewrites any Python file whose
formatting differs from ruff's output.  Equivalent to ``ci format`` but
with the ``--diff`` flag removed so files are actually rewritten.

----

``format markdown``
-------------------

Auto-format Markdown files with mdformat.

.. code-block:: bash

    scaldys-project format markdown

Executes ``uv run mdformat <targets>`` on discovered target Markdown files
(``README.md`` and any MkDocs documentation files in ``docs/``).  mdformat
rewrites any unformatted files **in place**.  If no target files exist or all
files are already correctly formatted, the command exits with code ``0``.
In a uv workspace the targets come from ``[format]`` in the root
``scaldys-project.toml`` and mdformat runs at the workspace root.

Typical workflow after a ``ci markdown`` failure::

    scaldys-project format markdown
    git add -p
    git commit

See :ref:`markdown_formatting_guide` for details.

----

Global behaviour
----------------

Project root discovery
^^^^^^^^^^^^^^^^^^^^^^

The ``build``, ``check``, ``publish``, ``ci`` and ``format`` commands resolve
the project root at startup by walking up the directory tree from ``cwd``
until a ``pyproject.toml`` file is found.  You can invoke them from any
subdirectory of your project.

Outside a uv workspace, the ``test`` command runs pytest in the **current
working directory**.  Run it from the project root.

.. _cli_targets:

uv workspaces: choosing the targets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When the project root belongs to a uv workspace (a parent ``pyproject.toml``
with ``[tool.uv.workspace]``), ``build`` (all subcommands), ``check``,
``test`` and ``publish`` act on one or more *members*:

- ``--package NAME`` / ``-p NAME`` (repeatable) selects members by name;
- ``--all-packages`` selects every member;
- with neither, the member containing the current directory is used;
- at a virtual workspace root, with neither, the command fails (exit code
  ``2``) and lists the members.

Selected members always run in topological order (libraries before the
members that depend on them) and the run stops at the first failure.  With
more than one target each one gets a header line.  The run always ends with
a summary table (see :ref:`cli_summary`).

Outside a workspace, ``--package`` and ``--all-packages`` are an error
(exit code ``2``).

``ci`` and ``format`` do not take these options: they always run once at
the workspace root.  ``init`` refuses to run inside a workspace.  See
:ref:`uv_workspaces` for the full guide.

.. _cli_summary:

Summary table
^^^^^^^^^^^^^

``build`` (all subcommands), ``check``, ``test`` and ``publish`` end with a
summary table listing each target with its version (``[project] version`` in
its ``pyproject.toml``) and its result.  The table is printed for every run:
a whole workspace, a single member, or a standalone project.  It is also
printed after a failure, so you can see which targets succeeded, which one
failed and which were not run::

          Build summary
    ┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
    ┃ Package ┃ Version ┃ Result  ┃
    ┡━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
    │ store   │ 1.4.0   │ ok      │
    │ report  │ 0.9.2   │ failed  │
    │ app     │ 2.1.0   │ not run │
    └─────────┴─────────┴─────────┘

The *Package* column shows the project directory name.  *Version* shows
``-`` when the version cannot be read (for example a dynamic version).

Logging
^^^^^^^

By default, ``INFO``-level messages are shown via Rich's formatted console
output. For ``ci``, ``format``, and ``test`` commands, this includes the
complete syntax of the underlying subprocess command (displayed in dim text).
Pass ``--verbose`` / ``-v`` to any command to enable ``DEBUG``-level output,
which includes all subprocess invocations and file operation details for all
commands (including ``build``).

Exit codes
^^^^^^^^^^

``scaldys-project`` exits with code ``0`` on success and non-zero on failure.
Failures are always accompanied by a descriptive error message.
