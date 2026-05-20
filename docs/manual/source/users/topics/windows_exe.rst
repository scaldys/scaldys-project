.. _windows_exe:

***************************
Windows Distribution Modes
***************************

``scaldys-project`` supports three deployment modes for distributing a Python
application to Windows users.  The active mode is controlled by
``deployment_mode`` in ``scaldys-project.toml``.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Mode
     - What it builds
     - When to use
   * - ``wheel_only`` (default)
     - Binary wheel only, no installer
     - Packages distributed via ``pip`` or ``uv``
   * - ``pyinstaller``
     - PyInstaller exe + Inno Setup installer
     - Most applications; no Python needed on end-user machine
   * - ``pyruntime``
     - Binary wheel + Inno Setup installer with a managed Python runtime
     - Apps that must coexist with Quarto, Jupyter, or another Python
       environment

Set the mode in ``scaldys-project.toml``:

.. code-block:: toml

    [windows]
    deployment_mode = "pyinstaller"   # or "pyruntime" or "wheel_only"

All modes share the Cython compilation step and produce a binary distribution
wheel.  What differs is how the application is launched on the end-user's
machine.


Shared steps (all modes)
========================

Cython compilation
------------------

If ``[cython] compiled_modules`` is non-empty in ``scaldys-project.toml``,
``scaldys-project`` first stages a copy of the source tree into
``build/compiled/``, compiles the specified modules to ``.pyd`` extension
files with Cython, and removes the corresponding ``.py`` files so the
compiled extensions are used instead.  See :ref:`cython_compilation` for
full details.

Distribution wheel
------------------

After the Cython step (or immediately, if Cython is disabled),
``scaldys-project`` builds a ``.pyd``-only distribution wheel from
``build/compiled/``.  This wheel contains compiled ``.pyd`` extension
modules only — no Python source files — which protects proprietary algorithm
details while still making the full package importable in a Python
environment.

The wheel is placed directly in ``dist/``:

.. code-block:: text

    dist/
        myapp-1.2.3-cp313-cp313-win_amd64.whl

In ``pyruntime`` mode the wheel is also staged into
``artifacts/portable/wheels/`` so that Inno Setup can bundle it into the
installer and ``setup_pyruntime.ps1`` can install it via
``uv pip install --find-links <wheels_dir>``.

.. note::

   The wheel build requires ``uv`` to be available on ``PATH``.  ``uv`` is
   already used throughout the rest of the build pipeline, so no additional
   installation is needed.

.. note::

   The wheel build is only meaningful when Cython compilation is enabled
   (``[cython] compiled_modules`` is non-empty).  If no modules are compiled,
   the resulting wheel is equivalent to a regular source wheel with no
   source-protection benefit.

How the wheel is built
~~~~~~~~~~~~~~~~~~~~~~

1. A copy of the project's ``pyproject.toml`` is written into
   ``build/compiled/`` so that setuptools can discover the package.
   The readme file referenced by the ``readme`` field in ``pyproject.toml``
   (e.g. ``README.md``) is also copied there so that setuptools can embed
   its contents as the package description in the wheel metadata.
2. The copy of ``pyproject.toml`` is patched to:

   - restrict package discovery to the project package only (excluding
     ``extra_hooks/`` and other top-level directories), and
   - declare ``*.pyd`` files as package data so that setuptools includes the
     compiled extensions in the wheel.

3. ``uv build --wheel`` is invoked from ``build/compiled/`` and the resulting
   ``.whl`` file is written to ``dist/``.


Mode 1: ``pyinstaller``
========================

``PyInstaller`` bundles the project into a self-contained one-directory
executable.  No Python installation is required on the end-user's machine.

Requirements
------------

Install the ``[windows]`` extra::

    uv add --dev "scaldys-project[windows]"

This installs ``PyInstaller``.

How it works
------------

PyInstaller is called programmatically after the Cython step with a fixed
set of options tuned for Windows distribution.

**One-directory bundle (``--onedir``)**
    PyInstaller runs in *one-directory* mode: it produces a folder
    containing the executable and all required libraries rather than a
    single merged ``exe``.  This avoids the slow startup time of a one-file
    build and makes antivirus software less likely to flag the executable
    during extraction.

**Console mode**
    The executable is built as a *console application* (``--console``) so
    that ``stdout`` / ``stderr`` output is visible in a terminal or can be
    redirected.

**UPX disabled**
    UPX compression is explicitly disabled (``--noupx``).  UPX-compressed
    binaries are frequently flagged by antivirus software because compression
    is a technique also used by malware packers.

**Module collection**
    PyInstaller is instructed to ``--collect-submodules`` for the top-level
    package, ensuring dynamically-imported submodules are included.

**Hook file handling**
    If an ``extra_hooks/`` directory exists in the compiled source tree and
    contains a file named ``hook_package.py``, ``scaldys-project`` renames it
    to ``hook-<package_name>.py`` so that PyInstaller discovers it correctly.
    Use this generic name in your source tree to keep hook files reusable
    across projects.

**Icon support**
    If ``<project_name>.ico`` is found in ``[windows] script_dir``, it is
    passed to PyInstaller via ``--icon`` and embedded in the executable.

Output
------

.. code-block:: text

    dist/
        myapp-1.2.3-cp313-cp313-win_amd64.whl
    artifacts/
        portable/
            bin/
                myapp.exe
                python313.dll
                _internal/         ← all imported packages and DLLs
        installer/
            setup.exe              ← built by the subsequent Inno Setup step

The ``build windows`` command then copies launcher scripts and documentation
into ``artifacts/portable/`` before invoking Inno Setup.

Build directories
-----------------

PyInstaller's intermediate working files are written to
``build/pyinstaller/``.  The ``build clean`` command removes this directory
along with all other build artefacts.

Common issues
-------------

**Missing modules at runtime**
    PyInstaller analyses imports statically.  Dynamic imports are not
    detected automatically.  Use ``--collect-submodules`` (already passed by
    ``scaldys-project``) or add hidden imports to your hook file:

    .. code-block:: python

        # hook-myapp.py
        hiddenimports = ["myapp.plugins.pdf", "myapp.plugins.csv"]

**Antivirus false positives**
    ``scaldys-project`` already disables UPX to reduce the likelihood of
    this.  If false positives persist, consider signing the executable with
    a code-signing certificate.

**Large bundle size**
    PyInstaller includes every imported package.  Audit your dependencies
    and remove unused ones.  The ``--exclude-module`` option can be added
    to a hook file to exclude known-unnecessary packages (e.g. ``tkinter``,
    ``unittest``).


Mode 2: ``pyruntime``
======================

Instead of a frozen executable, the application is installed into a
``uv``-managed Python virtual environment (``PythonRuntime``) on the
end-user's machine.  The launcher scripts activate that environment.

Use this mode when your application must coexist with Quarto, Jupyter, or
another tool that requires a real Python interpreter.  PyInstaller is not
used in this mode.

Requirements
------------

- ``.python-version`` at the project root (single source of truth for the
  Python version).
- ``uv.exe`` available on ``PATH`` at build time (it is bundled into the
  installer for end users).
- Inno Setup installed on the build machine.

How it works
------------

1. Cython compilation (if configured) + binary wheel build (see above).
2. ``setup_pyruntime.ps1``, ``uv.exe``, and ``.python-version`` are staged
   into ``artifacts/portable/bin/``.
3. The binary wheel is staged into ``artifacts/portable/wheels/`` so the
   installer and setup script can find it.
4. Launcher scripts, documentation, and examples are staged into
   ``artifacts/portable/``.
5. Inno Setup is invoked with ``/DPyruntimeMode=1``.

At install time, the Inno Setup script optionally runs
``setup_pyruntime.ps1`` with elevated privileges to create the
``PythonRuntime`` virtual environment inside the installation directory.

Online and offline installer sub-modes
---------------------------------------

``pyruntime`` mode supports two sub-modes for how the Python runtime is
delivered.  See :ref:`windows_installer` — *Online and offline installer
modes* for full details.

Output
------

.. code-block:: text

    dist/
        myapp-1.2.3-cp313-cp313-win_amd64.whl
    artifacts/
        portable/
            bin/
                setup_pyruntime.ps1
                uv.exe
                .python-version
                myapp_commandline.bat   ← copied from script_dir
                myapp_powershell.ps1
            wheels/
                myapp-1.2.3-cp313-cp313-win_amd64.whl
            documentation/
                <name>/
        installer/
            setup.exe


Mode 3: ``wheel_only``
=======================

Builds only the binary distribution wheel.  No installer and no launcher
scripts are produced.  Use this for packages distributed via ``pip`` or
``uv``.

Requirements
------------

No external tools beyond ``uv`` (already part of the build pipeline).
PyInstaller and Inno Setup are not required.  The Inno Setup script
(``.iss``) and launcher files (``.bat``, ``.ps1``) do not need to exist in
the packaging directory.

How it works
------------

1. Cython compilation (if configured).
2. Binary wheel built and placed in ``dist/``.
3. Build finishes — no installer step.

Output
------

.. code-block:: text

    dist/
        myapp-1.2.3-cp313-cp313-win_amd64.whl
    artifacts/
        documentation/
            <name>/             ← only present if public_doc_dirs is non-empty
