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
    OutputDir=..\..\dist\setup
    OutputBaseFilename=MyApp-Setup-{#MyAppVersion}
    Compression=lzma
    SolidCompression=yes

    [Files]
    Source: "..\..\dist\pyinstaller\bin\*"; DestDir: "{app}\bin"; Flags: recursesubdirs

    [Icons]
    Name: "{group}\MyApp"; Filename: "{app}\bin\myapp.exe"
    Name: "{commondesktop}\MyApp"; Filename: "{app}\bin\myapp.exe"

    [Run]
    Filename: "{app}\bin\myapp.exe"; Description: "Launch MyApp"; Flags: postinstall

.. tip::

   Use relative paths in the ``.iss`` script relative to the script's own
   location (``packaging/windows/``).  The paths ``..\..\dist\pyinstaller\bin\*``
   and ``..\..\dist\setup`` navigate from the packaging directory to the
   project root's ``dist/`` output.

Launcher scripts
----------------

Launcher scripts are copied into ``dist/pyinstaller/`` alongside the
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
   ``[windows] script_dir`` are copied to ``dist/pyinstaller/``.

2. **Copy documentation** — for each directory listed in ``[docs] dist_dirs``
   in ``builder.toml``, the HTML output (from ``build/<name>/html/``) is
   copied to ``dist/pyinstaller/documentation/<name>/``.

3. **Copy examples** (optional) — if an ``examples/`` directory exists in
   the project root, it is copied to ``dist/pyinstaller/examples/``.

4. **Run Inno Setup** — ``ISCC.exe`` is invoked with the ``.iss`` script and
   the version define::

       ISCC.exe /DMyAppVersion=1.2.3 packaging\windows\myapp.iss

Output location
===============

.. code-block:: text

    dist/
        setup/
            MyApp-Setup-1.2.3.exe   ← Windows installer

The output filename and location are controlled entirely by the ``[Setup]``
section of your ``.iss`` script.

Skipping Inno Setup
===================

If Inno Setup is not installed or not found, the installer step logs a
warning and exits cleanly without failing.  This allows the rest of the
build (docs, exe) to succeed even on machines without Inno Setup.
