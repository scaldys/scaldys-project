.. _windows_installer:

**************************
Windows Installer Creation
**************************

``scaldys-project build windows`` assembles the final distribution directory
and — in ``pyinstaller`` and ``pyruntime`` modes — invokes Inno Setup to
produce a polished Windows installer (``.exe``).  In ``wheel_only`` mode the
installer step is skipped entirely.

Requirements
============

- **Inno Setup** must be installed on the build machine (``pyinstaller`` and
  ``pyruntime`` modes only).  Download it from
  `jrsoftware.org <https://jrsoftware.org/isinfo.php>`_.  ``scaldys-project``
  looks for ``ISCC.exe`` in the default ``%ProgramFiles%\Inno Setup 6\``
  location or on ``PATH``.

Packaging files
===============

Place the following files in the directory specified by
``[windows] script_dir`` in ``scaldys.toml`` (default: ``packaging/windows/``):

.. code-block:: text

    packaging/windows/
        myapp.iss                   # Inno Setup script (required in pyinstaller/pyruntime mode)
        myapp_commandline.bat       # Command-line launcher (required in pyinstaller/pyruntime mode)
        myapp_powershell.ps1        # PowerShell launcher (required in pyinstaller/pyruntime mode)
        myapp.ico                   # Application icon (optional)
        setup_pyruntime.ps1         # Runtime setup script (required in pyruntime mode)

Replace ``myapp`` with the project name as declared under ``[project] name``
in ``pyproject.toml``.  The name is normalised to lowercase with hyphens
replaced by underscores.

In ``wheel_only`` mode, none of these files are required.

Inno Setup script (``myapp.iss``)
----------------------------------

Write a standard Inno Setup script.  ``scaldys-project`` injects the project
version automatically via the ``/DMyAppVersion`` define and — in
``pyruntime`` mode — passes ``/DPyruntimeMode=1`` and optionally
``/DPythonRuntimeDir=<path>``.

To support both deployment modes from a single ``.iss`` file, use
preprocessor conditionals:

.. code-block:: ini

    ; Example: myapp.iss supporting pyinstaller and pyruntime modes

    [Setup]
    AppName=My Application
    AppVersion={#MyAppVersion}
    DefaultDirName={autopf}\MyApp
    OutputDir=..\..\artifacts\installer
    OutputBaseFilename=setup

    [Tasks]
    Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked
    #ifdef PyruntimeMode
    Name: "pyruntime"; Description: "Python runtime environment"; GroupDescription: "Optional components:"
    #endif

    [Files]
    Source: "..\..\artifacts\portable\*"; DestDir: "{app}"; Flags: createallsubdirs recursesubdirs ignoreversion

    #ifdef PyruntimeMode
      #ifdef PythonRuntimeDir
    Source: "{#PythonRuntimeDir}\*"; DestDir: "{app}\PythonRuntime"; Flags: createallsubdirs recursesubdirs ignoreversion; Tasks: pyruntime
      #endif
    #endif

    [UninstallRun]
    #ifdef PyruntimeMode
    Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""if (Test-Path '{app}\PythonRuntime') {{ Remove-Item -Recurse -Force '{app}\PythonRuntime' }}"" "; Flags: runhidden; RunOnceId: "RemovePythonRuntime"
    Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""if (Test-Path '{app}\wheels') {{ Remove-Item -Recurse -Force '{app}\wheels' }}"" "; Flags: runhidden; RunOnceId: "RemoveWheels"
    #endif

.. tip::

   Use relative paths in the ``.iss`` script relative to the script's own
   location (``packaging/windows/``).  The paths ``..\..\artifacts\portable\*``
   and ``..\..\artifacts\installer`` navigate from the packaging directory to
   the project root's ``artifacts/`` output directory.

Launcher scripts
----------------

Launcher scripts are copied into ``artifacts/portable/bin/`` so they are included
in the installer.  They must auto-detect the deployment mode at run time,
since a single ``.iss`` supports both ``pyinstaller`` and ``pyruntime``
modes.

**myapp_commandline.bat** — opens a command prompt:

.. code-block:: bat

    @echo off
    set "SCRIPT_DIR=%~dp0"

    if exist "%SCRIPT_DIR%myapp.exe" (
        set "PATH=%SCRIPT_DIR%;%PATH%"
        cmd /k "myapp.exe --help"
    ) else (
        set "PYRUNTIME_ACTIVATE=%SCRIPT_DIR%..\PythonRuntime\Scripts\activate.bat"
        if exist "%PYRUNTIME_ACTIVATE%" (
            call "%PYRUNTIME_ACTIVATE%"
            cmd /k "myapp --help"
        ) else (
            echo ERROR: Application not found. Check your installation or run setup_pyruntime.ps1 as administrator.
            pause
        )
    )

**myapp_powershell.ps1** — opens a PowerShell session:

.. code-block:: powershell

    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Clear-Host

    $pyinstallerExe    = Join-Path $scriptDir 'myapp.exe'
    $pyruntimeActivate = Join-Path (Split-Path -Parent $scriptDir) 'PythonRuntime\Scripts\Activate.ps1'

    if (Test-Path $pyinstallerExe) {
        $env:Path += ";$scriptDir"
        myapp.exe --help
    } elseif (Test-Path $pyruntimeActivate) {
        & $pyruntimeActivate
        myapp --help
    } else {
        Write-Warning "Application not found. Check your installation or run setup_pyruntime.ps1 as administrator."
    }

The launchers check for ``myapp.exe`` first (``pyinstaller`` mode).  If
absent they look for the PythonRuntime venv activation script (``pyruntime``
mode).

Application icon
----------------

If ``myapp.ico`` is present, it is passed to PyInstaller (embedded in the
``.exe``) and should also be referenced in the ``.iss`` script for the
Start Menu and Desktop shortcuts.

How it works
============

The installer step performs the following actions in sequence, depending on
the active ``deployment_mode``:

1. **Copy launcher scripts** — ``.bat`` and ``.ps1`` files from
   ``[windows] script_dir`` are copied to ``artifacts/portable/bin/``.

2. **Copy documentation** — for each directory listed in ``[docs] public_doc_dirs``
   in ``scaldys.toml``, the HTML output (from ``build/<name>/html/``) is
   copied to both ``artifacts/portable/documentation/<name>/`` (bundled with
   the portable package) and ``artifacts/documentation/<name>/`` (standalone
   docs only).

3. **Copy examples** (optional) — if an ``examples/`` directory exists in
   the project root, it is copied to ``artifacts/portable/examples/``.

4. **Stage PythonRuntime files** (``pyruntime`` mode only) — copies
   ``setup_pyruntime.ps1``, ``uv.exe``, and ``.python-version`` into
   ``artifacts/portable/bin/``, and stages the binary wheel into
   ``artifacts/portable/wheels/``.

5. **Build PythonRuntime** (``pyruntime`` mode, offline sub-mode only) — if
   ``[windows] bundle_pyruntime = true`` is set in ``scaldys.toml``,
   ``scaldys-project`` pre-builds a ``uv``-managed Python virtual environment
   at ``artifacts/pyruntime/`` containing all runtime dependencies.  See
   `Online and offline installer modes`_ below.

6. **Run Inno Setup** — ``ISCC.exe`` is invoked with the ``.iss`` script,
   the version define, and — in ``pyruntime`` mode — additional defines::

       # pyinstaller mode:
       ISCC.exe /DMyAppVersion=1.2.3 packaging\windows\myapp.iss

       # pyruntime mode, online:
       ISCC.exe /DMyAppVersion=1.2.3 /DPyruntimeMode=1 packaging\windows\myapp.iss

       # pyruntime mode, offline:
       ISCC.exe /DMyAppVersion=1.2.3 /DPyruntimeMode=1 /DPythonRuntimeDir=..\..\artifacts\pyruntime packaging\windows\myapp.iss

Online and offline installer modes
===================================

These sub-modes are only relevant when ``deployment_mode = "pyruntime"``.
They control how the Python runtime environment is delivered to end users.

**Online mode** (default)
    The installer downloads Python at install time using ``uv``.  No
    pre-built environment is bundled — the ``setup.exe`` is smaller but the
    end user's machine must have internet access during installation.

    To use online mode, omit ``bundle_pyruntime`` from ``scaldys.toml`` (or
    set it to ``false``).  The Inno Setup script should call
    ``setup_pyruntime.ps1`` during install to create the environment.

**Offline mode**
    A complete PythonRuntime virtual environment is pre-built on the build
    machine and embedded inside ``setup.exe``.  Installation succeeds on
    air-gapped machines.  The ``setup.exe`` is correspondingly larger.

    To enable offline mode, set in ``scaldys.toml``:

    .. code-block:: toml

        [windows]
        deployment_mode = "pyruntime"
        bundle_pyruntime = true

    During the build, ``scaldys-project``:

    1. Reads the required Python version from ``.python-version`` at the
       project root.
    2. Installs that Python version via ``uv python install``.
    3. Creates a virtual environment at ``artifacts/pyruntime/`` and installs
       ``jupyter``, ``pyyaml``, and the project's binary wheel
       (from ``dist/``) into it.
    4. Passes ``/DPythonRuntimeDir=<path>`` to Inno Setup so the script
       can bundle the pre-built environment.

    Your ``.iss`` script should use the ``PythonRuntimeDir`` define
    conditionally:

    .. code-block:: ini

        ; Bundle offline PythonRuntime if provided at build time
        #ifdef PyruntimeMode
          #ifdef PythonRuntimeDir
        Source: "{#PythonRuntimeDir}\*"; DestDir: "{app}\PythonRuntime"; Flags: recursesubdirs
          #endif
        #endif

.. note::

   Both online and offline sub-modes require ``.python-version`` to exist
   at the project root (see :ref:`compliance_checking` — Rule 9).  In
   online mode the file is copied into ``bin\`` so ``setup_pyruntime.ps1``
   can read it at install time.  In offline mode it is used during the
   build to select the correct Python version.

Output location
===============

.. code-block:: text

    artifacts/
        installer/
            setup.exe   ← Windows installer (from Inno Setup)

The output filename and location are controlled by the ``[Setup]``
section of your ``.iss`` script.
