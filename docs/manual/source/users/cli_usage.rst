.. _cli_usage:

CLI Reference
=============

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
    └── build
        └── windows
            ├── docs
            ├── exe
            ├── installer
            ├── all
            └── clean

----

``build windows docs``
-----------------------

Build the Sphinx documentation for the project.

.. code-block:: bash

    scaldys-builder build windows docs [OPTIONS]

**What it does**

1. Builds the *user guide* from ``docs/manual/`` into two HTML formats:
   standard multi-page HTML and a single-page HTML (``singlehtml``).
2. Runs ``sphinx-apidoc`` over the source tree to generate API stubs, then
   builds the *developer guide* into HTML.

**Output locations**

.. code-block:: text

    build/manual/html/          ← user guide (multi-page)
    build/manual/singlehtml/    ← user guide (single page)
    build/developer_guide/html/ ← developer / API guide

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

    dist/pyinstaller/bin/   ← executable + all supporting libraries

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
   from ``build/manual/singlehtml/`` into ``dist/pyinstaller/``.
2. Copies any example files from ``examples/`` (if the directory exists).
3. Runs ``ISCC.exe`` with the ``.iss`` script found in
   ``[windows] script_dir``, injecting the project version automatically.

**Output location**

.. code-block:: text

    dist/setup/     ← Windows installer executable

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

Executes ``docs`` → ``exe`` → ``installer`` in sequence, with a Rich
progress bar tracking the overall workflow. Any stage failure stops the build
and reports the error.

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
