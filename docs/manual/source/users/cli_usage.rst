.. _cli_usage:

CLI Reference
=============

This page is a complete reference for every ``scaldys-builder`` command and
option.  If you have not yet set up your project, start with :ref:`quickstart`.

``scaldys-builder`` is invoked from the command line. All commands auto-discover
the project root by walking up the directory tree from the current working
directory until a ``pyproject.toml`` file is found.

Top-level usage::

    scaldys-builder [OPTIONS] COMMAND [ARGS]...

Options
-------

.. option:: --help

   Show the help message and exit.  Available at every command level.

Command tree
------------

.. code-block:: text

    scaldys-builder
    ├── check
    └── build
        ├── all
        ├── docs
        ├── windows
        └── clean

----

``check``
----------

Validate that the current project meets all scaldys-builder requirements
without running any build step.

.. code-block:: bash

    scaldys-builder check [OPTIONS]

**What it does**

Runs the full compliance check and reports any issues found.
Exits with code ``0`` if the project is compliant, or code ``1`` if any
requirement is not met.  This is identical to the automatic check that runs
at the start of ``build windows`` and ``build all``, but without triggering
a build.

The rules that are evaluated depend on the ``deployment_mode`` setting in
``builder.toml``.  In ``wheel_only`` mode the Inno Setup script and launcher
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

``build all``
--------------

Run the complete end-to-end build workflow: documentation and Windows
distribution.

.. code-block:: bash

    scaldys-builder build all [OPTIONS]

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

    scaldys-builder build docs [OPTIONS]

**What it does**

Scans every immediate subdirectory of ``docs/`` and builds each one as an
independent documentation unit.  The engine (Sphinx, MkDocs, …) is
auto-detected from each subdirectory's contents.

For each Sphinx unit (``source/conf.py`` present), two HTML formats are
produced: standard multi-page HTML and single-page HTML.  For units listed
in ``[docs] internal_doc_dirs`` in ``builder.toml``, ``sphinx-apidoc`` runs
first to generate ``.rst`` stubs from source code docstrings.

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

    scaldys-builder build windows [OPTIONS]

**What it does**

Reads ``deployment_mode`` from ``builder.toml`` (default: ``"pyinstaller"``)
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

    scaldys-builder build clean [OPTIONS]

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

Global behaviour
----------------

Project root discovery
^^^^^^^^^^^^^^^^^^^^^^

Every command resolves the project root at startup by walking up the
directory tree from ``cwd`` and finding the first directory that contains a
``pyproject.toml`` file.  You can invoke ``scaldys-builder`` from any
subdirectory of your project.

Logging
^^^^^^^

By default, ``INFO``-level messages are shown via Rich's formatted console
output.  Pass ``--verbose`` / ``-v`` to any command to enable ``DEBUG``-level
output, which includes all subprocess invocations and file operation details.

Exit codes
^^^^^^^^^^

``scaldys-builder`` exits with code ``0`` on success and non-zero on failure.
Failures are always accompanied by a descriptive error message.
