.. _configuration:

*************
Configuration
*************

``scaldys-project`` reads project-specific build settings from a
``scaldys-project.toml`` file in the project root.  Every setting has a default, so
the file is entirely optional — pure-Python projects with packaging files in
the default location require no configuration at all.

File location
=============

Place ``scaldys-project.toml`` alongside ``pyproject.toml`` in your project root::

    my-project/
        pyproject.toml
        scaldys-project.toml        ← optional
        src/
        packaging/windows/

Sections
========

``[cython]``
------------

Controls Cython compilation.

.. code-block:: toml

    [cython]
    compiled_modules = [
        "myapp.core.engine",
        "myapp.core.crypto",
    ]
    source_root = "src"

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Key
     - Default
     - Description
   * - ``compiled_modules``
     - ``[]``
     - List of fully-qualified dotted module paths to compile with Cython.
       An empty list (the default) disables Cython; source files are staged
       as-is for PyInstaller.
   * - ``source_root``
     - ``"src"``
     - Directory relative to the project root that contains your Python
       source packages.  For a ``src``-layout project this is ``"src"``; for
       a flat layout it is typically ``"."`` or the package name itself.

**Example — no Cython compilation** (pure-Python project)

.. code-block:: toml

    # [cython] section omitted — defaults apply

**Example — compile selected modules**

.. code-block:: toml

    [cython]
    compiled_modules = [
        "myapp.core.engine",   # performance-critical inner loop
        "myapp.core.crypto",   # obfuscation: hide algorithm details
    ]

See :ref:`cython_compilation` for a full explanation of how compilation works.

``[docs]``
----------

Controls which documentation units are distributed to end users and which
contain internal developer documentation (with an optional ``sphinx-apidoc``
pre-pass).

.. code-block:: toml

    [docs]
    public_doc_dirs = ["manual"]
    internal_doc_dirs = ["developer_guide"]

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Key
     - Default
     - Description
   * - ``public_doc_dirs``
     - ``[]``
     - List of subdirectory names under ``docs/`` whose built HTML output
       (``build/<name>/html/``) is copied into the distribution artefacts:
       ``dist/portable/documentation/<name>/`` (alongside the portable package)
       and ``dist/documentation/<name>/`` (standalone documentation copy).
       These are the documentation units destined for end users of the program.
       An empty list means no documentation is distributed.
   * - ``internal_doc_dirs``
     - ``[]``
     - List of subdirectory names containing internal documentation for
       developers of the program — not distributed to end users.  For each
       listed name, a ``sphinx-apidoc`` pre-pass runs before ``sphinx-build``
       to generate ``.rst`` stubs from docstrings.  Must be a subset of the
       Sphinx directories (those containing ``source/conf.py``).

**Example — distribute one unit, generate one unit from source code**

.. code-block:: toml

    [docs]
    public_doc_dirs = ["manual"]
    internal_doc_dirs = ["developer_guide"]

See :ref:`documentation_building` for a full explanation of how the doc
build works.

``[windows]``
-------------

Controls Windows-specific packaging paths, the deployment strategy, and
distribution options.

.. code-block:: toml

    [windows]
    script_dir = "packaging/windows"
    deployment_mode = "pyinstaller"
    bundle_pyruntime = false

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Key
     - Default
     - Description
   * - ``script_dir``
     - ``"packaging/windows"``
     - Directory relative to the project root containing the Windows
       packaging files: Inno Setup script (``.iss``), launcher scripts
       (``.bat``, ``.ps1``), and the optional application icon (``.ico``).
   * - ``deployment_mode``
     - ``"pyinstaller"``
     - Controls how the application is packaged for Windows users.
       Three values are supported:

       ``"pyinstaller"`` (default)
           PyInstaller bundles your application into a self-contained
           executable directory.  Inno Setup wraps it into a setup ``.exe``.
           No Python installation is required on the end-user's machine.

       ``"pyruntime"``
           PyInstaller is *not* used.  The installer deploys a managed
           Python virtual environment (``PythonRuntime``) into the
           installation directory.  The launcher scripts activate that
           environment.  Use this mode when the application must coexist
           with tools such as Quarto or Jupyter that require a real Python
           interpreter.  Requires ``.python-version`` at the project root.

       ``"wheel_only"``
           Builds a binary distribution wheel only.  No Windows installer
           is created.  Use this for packages distributed via ``pip`` or
           ``uv`` rather than a setup ``.exe``.  The Inno Setup script and
           launcher files are not required.

       See :ref:`windows_exe` for a full description of each mode.
   * - ``bundle_pyruntime``
     - ``false``
     - *Only meaningful when* ``deployment_mode = "pyruntime"``.
       When ``true``, pre-builds a PythonRuntime virtual environment at
       ``dist/pyruntime/`` and passes its path to Inno Setup as
       ``/DPythonRuntimeDir``, enabling an offline installer that requires
       no internet access on the end-user's machine.  Requires
       ``.python-version`` at the project root and ``uv`` on ``PATH``.
       See :ref:`windows_installer` — *Online and offline installer modes*.

See :ref:`windows_installer` for details on what each packaging file should
contain.

Complete example
================

.. code-block:: toml

    [cython]
    compiled_modules = [
        "myapp.core.engine",
        "myapp.core.crypto",
    ]
    source_root = "src"

    [windows]
    script_dir = "packaging/windows"
    deployment_mode = "pyinstaller"

    [docs]
    public_doc_dirs = ["manual"]
    internal_doc_dirs = ["developer_guide"]

Annotated reference file
========================

For a single copy-paste-ready block that lists every option with inline
comments, see :ref:`scaldys_project_toml_reference`.

Defaults summary
================

If ``scaldys-project.toml`` is absent, or a section / key is missing, the following
defaults apply:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Setting
     - Default value
   * - ``cython.compiled_modules``
     - ``[]`` (Cython disabled)
   * - ``cython.source_root``
     - ``"src"``
   * - ``windows.script_dir``
     - ``"packaging/windows"``
   * - ``windows.deployment_mode``
     - ``"pyinstaller"``
   * - ``windows.bundle_pyruntime``
     - ``false`` (online installer; only applies in ``pyruntime`` mode)
   * - ``docs.public_doc_dirs``
     - ``[]`` (no documentation distributed)
   * - ``docs.internal_doc_dirs``
     - ``[]`` (no apidoc pre-pass)
