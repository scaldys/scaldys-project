.. _windows_installer:

**************************
Windows Installer Creation
**************************

``scaldys-builder build windows installer`` assembles the final distribution
directory and invokes Inno Setup to produce a polished Windows installer
(``.exe``).

Requirements
============

- **Inno Setup** must be installed on the build machine.  Download it from
  `jrsoftware.org <https://jrsoftware.org/isinfo.php>`_.  ``scaldys-builder``
  looks for ``ISCC.exe`` in the default ``%ProgramFiles%\Inno Setup 6\``
  location or on ``PATH``.  If Inno Setup is not found the step is skipped
  with a warning rather than aborting the build.

Packaging files
===============

Place the following files in the directory specified by
``[windows] script_dir`` in ``builder.toml`` (default: ``packaging/windows/``):

.. code-block:: text

    packaging/windows/
        myapp.iss                   # Inno Setup script (required)
        myapp_commandline.bat       # Command-line launcher (required)
        myapp_powershell.ps1        # PowerShell launcher (required)
        myapp.ico                   # Application icon (optional)

Replace ``myapp`` with the project name as declared under ``[project] name``
in ``pyproject.toml``.  The name is normalised to lowercase with hyphens
replaced by underscores.

Inno Setup script (``myapp.iss``)
----------------------------------

Write a standard Inno Setup script.  ``scaldys-builder`` injects the project
version automatically via the ``/DMyAppVersion`` define, so use that symbol
in your script:

.. code-block:: ini

    [Setup]
    AppName=My Application
    AppVersion={#MyAppVersion}
    AppPublisher=My Company
    DefaultDirName={autopf}\MyApp
    DefaultGroupName=MyApp
    OutputDir=..\..\dist\installer
    OutputBaseFilename=MyApp-Setup-{#MyAppVersion}
    Compression=lzma
    SolidCompression=yes

    [Files]
    Source: "..\..\dist\portable\bin\*"; DestDir: "{app}\bin"; Flags: recursesubdirs

    [Icons]
    Name: "{group}\MyApp"; Filename: "{app}\bin\myapp.exe"
    Name: "{commondesktop}\MyApp"; Filename: "{app}\bin\myapp.exe"

    [Run]
    Filename: "{app}\bin\myapp.exe"; Description: "Launch MyApp"; Flags: postinstall

.. tip::

   Use relative paths in the ``.iss`` script relative to the script's own
   location (``packaging/windows/``).  The paths ``..\..\dist\portable\bin\*``
   and ``..\..\dist\installer`` navigate from the packaging directory to the
   project root's ``dist/`` output.

Launcher scripts
----------------

Launcher scripts are copied into ``dist/portable/`` alongside the
executable bundle so they are included in the installer.

**myapp_commandline.bat** — opens a command prompt in the application directory:

.. code-block:: bat

    @echo off
    cd /d "%~dp0bin"
    cmd /k "myapp.exe %*"

**myapp_powershell.ps1** — opens a PowerShell session in the application directory:

.. code-block:: powershell

    Set-Location -Path "$PSScriptRoot\bin"
    & ".\myapp.exe" @args

Application icon
----------------

If ``myapp.ico`` is present, it is passed to PyInstaller (embedded in the
``.exe``) and should also be referenced in the ``.iss`` script for the
Start Menu and Desktop shortcuts.

How it works
============

The installer step performs the following actions in sequence:

1. **Copy launcher scripts** — ``.bat`` and ``.ps1`` files from
   ``[windows] script_dir`` are copied to ``dist/portable/``.

2. **Copy documentation** — for each directory listed in ``[docs] public_doc_dirs``
   in ``builder.toml``, the HTML output (from ``build/<name>/html/``) is
   copied to both ``dist/portable/documentation/<name>/`` (bundled with the
   portable package) and ``dist/documentation/<name>/`` (standalone docs only).

3. **Copy examples** (optional) — if an ``examples/`` directory exists in
   the project root, it is copied to ``dist/portable/examples/``.

4. **Build PythonRuntime** (optional, offline mode only) — if
   ``[windows] bundle_pyruntime = true`` is set in ``builder.toml``,
   ``scaldys-builder`` pre-builds a ``uv``-managed Python virtual environment
   at ``dist/pyruntime/`` containing all runtime dependencies.  See
   `Online and offline installer modes`_ below.

5. **Run Inno Setup** — ``ISCC.exe`` is invoked with the ``.iss`` script,
   the version define, and — in offline mode — the ``PythonRuntimeDir``
   define pointing to the pre-built environment::

       # online mode (no pre-built runtime):
       ISCC.exe /DMyAppVersion=1.2.3 packaging\windows\myapp.iss

       # offline mode (pre-built runtime bundled):
       ISCC.exe /DMyAppVersion=1.2.3 /DPythonRuntimeDir=..\..\dist\pyruntime packaging\windows\myapp.iss

Online and offline installer modes
===================================

``scaldys-builder`` supports two distribution modes for projects that require
a Python runtime environment alongside the application (e.g. to run Jupyter
notebooks or execute Python scripts at end-user sites).

**Online mode** (default)
    The installer downloads Python at install time using ``uv``.  No
    pre-built environment is bundled — the ``setup.exe`` is smaller but the
    end user's machine must have internet access during installation.

    To use online mode, omit ``bundle_pyruntime`` from ``builder.toml`` (or
    set it to ``false``).  The Inno Setup script should call
    ``setup_pyruntime.ps1`` during install to create the environment.

**Offline mode**
    A complete PythonRuntime virtual environment is pre-built on the build
    machine and embedded inside ``setup.exe``.  Installation succeeds on
    air-gapped machines.  The ``setup.exe`` is correspondingly larger.

    To enable offline mode, set in ``builder.toml``:

    .. code-block:: toml

        [windows]
        bundle_pyruntime = true

    During the build, ``scaldys-builder``:

    1. Reads the required Python version from ``.python-version`` at the
       project root.
    2. Installs that Python version via ``uv python install``.
    3. Creates a virtual environment at ``dist/pyruntime/`` and installs
       ``jupyter``, ``pyyaml``, and the project's distribution wheel
       (from ``dist/portable/bin/wheels/``) into it.
    4. Passes ``/DPythonRuntimeDir=<path>`` to Inno Setup so the script
       can bundle the pre-built environment.

    Your ``.iss`` script should use the ``PythonRuntimeDir`` define
    conditionally:

    .. code-block:: ini

        ; Bundle offline PythonRuntime if provided at build time
        #ifdef PythonRuntimeDir
        [Files]
        Source: "{#PythonRuntimeDir}\*"; DestDir: "{app}\PythonRuntime"; Flags: recursesubdirs
        #endif

.. note::

   Both modes require ``.python-version`` to exist at the project root (see
   :ref:`compliance_checking` — Rule 9).  In online mode the file is copied
   into ``bin\`` so ``setup_pyruntime.ps1`` can read it at install time.  In
   offline mode it is used during the build to select the correct Python
   version.

Output location
===============

.. code-block:: text

    dist/
        installer/
            MyApp-Setup-1.2.3.exe   ← Windows installer

The output filename and location are controlled entirely by the ``[Setup]``
section of your ``.iss`` script.

Skipping Inno Setup
===================

If Inno Setup is not installed or not found, the installer step logs a
warning and exits cleanly without failing.  This allows the rest of the
build (docs, exe) to succeed even on machines without Inno Setup.
