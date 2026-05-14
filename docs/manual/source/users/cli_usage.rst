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
        └── windows
            ├── docs
            ├── exe
            ├── installer
            ├── all
            └── clean

----

``check``
----------

Validate that the current project meets all scaldys-builder requirements
without running any build step.

.. code-block:: bash

    scaldys-builder check [OPTIONS]

**What it does**

Runs the full compliance check (rules 1–8) and reports any issues found.
Exits with code ``0`` if the project is compliant, or code ``1`` if any
requirement is not met.  This is identical to the automatic check that runs
at the start of ``exe``, ``installer``, and ``all``, but without triggering
a build.

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

``build windows docs``
-----------------------

Build the Sphinx documentation for the project.

.. code-block:: bash

    scaldys-builder build windows docs [OPTIONS]

**What it does**

Scans every immediate subdirectory of ``docs/`` and builds each one as an
independent documentation unit.  The engine (Sphinx, MkDocs, …) is
auto-detected from each subdirectory's contents.

For each Sphinx unit (``source/conf.py`` present), two HTML formats are
produced: standard multi-page HTML and single-page HTML.  For units listed
in ``[docs] apidoc_dirs`` in ``builder.toml``, ``sphinx-apidoc`` runs first
to generate ``.rst`` stubs from source code docstrings.

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

``build windows exe``
----------------------

Compile optional Cython modules and bundle the project into a standalone
Windows executable using PyInstaller.

.. code-block:: bash

    scaldys-builder build windows exe [OPTIONS]

**What it does**

1. **Cython step** (only if ``compiled_modules`` is non-empty in
   ``builder.toml``): stages source files to ``build/compiled/``, compiles
   the specified modules to ``.pyd`` extension files, and removes the
   corresponding ``.py`` files so PyInstaller picks up the native extensions.
2. **PyInstaller step**: bundles the staged source tree into a
   one-directory executable.

**Output location**

.. code-block:: text

    dist/portable/bin/   ← executable + all supporting libraries

**Compliance check**: Before running, verifies that the source package
directory and ``__main__.py`` entry point exist.  See :ref:`compliance_checking`.

**Pre-flight requirement**: PyInstaller must be installed.
Install it via the ``[windows]`` extra.

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

``build windows installer``
----------------------------

Prepare the final distribution directory and create a Windows installer using
Inno Setup.

.. code-block:: bash

    scaldys-builder build windows installer [OPTIONS]

**What it does**

1. Copies launcher scripts (``.bat``, ``.ps1``) and the HTML documentation
   for each directory listed in ``[docs] dist_dirs`` (``builder.toml``) from
   ``build/<name>/html/`` into ``dist/portable/documentation/<name>/``.
2. Copies any example files from ``examples/`` (if the directory exists).
3. Runs ``ISCC.exe`` with the ``.iss`` script found in
   ``[windows] script_dir``, injecting the project version automatically.

**Output location**

.. code-block:: text

    dist/installer/     ← Windows installer executable

**Compliance check**: Before running, verifies that the Windows packaging
directory, ``.iss`` script, and launcher scripts exist.  See
:ref:`compliance_checking`.

**Note**: If Inno Setup is not found, this step is skipped with a warning
rather than failing the build.

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

``build windows all``
----------------------

Run the complete end-to-end Windows build workflow.

.. code-block:: bash

    scaldys-builder build windows all [OPTIONS]

**What it does**

Runs the full compliance check (all rules) and pre-flight checks first, then
executes ``docs`` → ``exe`` → ``installer`` in sequence, with a Rich progress
bar tracking the overall workflow.  Any stage failure stops the build and
reports the error.

Also performs an OneDrive synchronisation check at startup: if OneDrive is
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

``build windows clean``
------------------------

Remove all intermediate and final build artefacts.

.. code-block:: bash

    scaldys-builder build windows clean [OPTIONS]

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
