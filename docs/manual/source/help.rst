.. _get_help:

********
Get Help
********

Built-in help
=============

Every ``scaldys-project`` command has a ``--help`` option that describes its
usage and options::

    scaldys-project --help
    scaldys-project build --help
    scaldys-project build all --help
    scaldys-project build windows --help

Verbose output
==============

If a build step fails or behaves unexpectedly, re-run the command with
``--verbose`` / ``-v`` to enable debug-level logging.  This prints every
subprocess invocation, file operation, and tool discovery step::

    scaldys-project build all --verbose

The extra output often identifies the root cause directly (missing tool,
wrong path, locked file, etc.).

Common issues
=============

"No module named …" at runtime
------------------------------

A module present in your source tree is missing from the built executable.
PyInstaller's static analysis may not have detected the import.  Add the
module to the ``hiddenimports`` list in your hook file — see
:ref:`windows_exe` for details.

Build fails with "compiler not found"
-------------------------------------

Cython compilation requires MSVC.  Open a *Developer Command Prompt for
Visual Studio* (or run ``vcvarsall.bat``) so that ``cl.exe`` is on
``PATH``, then retry.  See :ref:`cython_compilation` for details.

Inno Setup step is skipped
--------------------------

``ISCC.exe`` was not found.  Install Inno Setup from
`jrsoftware.org <https://jrsoftware.org/isinfo.php>`_ to the default
``%ProgramFiles%\Inno Setup 6\`` location, or add its directory to
``PATH``.  See :ref:`windows_installer` for details.

Files locked by OneDrive
------------------------

If your project tree is inside a OneDrive-synced folder, OneDrive may hold
read locks on files during synchronisation.  ``scaldys-project`` detects
active OneDrive sync and warns you at startup.  Wait for sync to complete or
pause OneDrive before building.

Reporting issues and requesting features
=========================================

Please report bugs and request new features on the project's GitHub issue
tracker:

  https://github.com/scaldys/scaldys-project/issues

When reporting a bug, include:

- The full command you ran.
- The output with ``--verbose`` enabled.
- Your Python version (``python --version``), OS version, and
  ``scaldys-project`` version (``scaldys-project --version`` if available,
  otherwise check ``pyproject.toml``).
