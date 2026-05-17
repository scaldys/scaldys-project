.. _compliance_checking:

********************
Project Compliance
********************

Before running any build step, ``scaldys-builder`` automatically validates
that your project has the required files and structure.  All issues are
collected and reported together — so you can fix everything in one pass —
then the tool exits without starting the build.

You can also run the check manually at any time without triggering a build::

    scaldys-builder check

This lets you verify a freshly cloned project or confirm your setup before
investing time in a full build.

Sample output
=============

When the project is fully set up:

.. code-block:: text

    INFO  Checking project compliance...
    INFO  ✓ Project is compliant.

When issues are found:

.. code-block:: text

    INFO  Checking project compliance...
    ERROR Project compliance check failed — 2 issue(s) must be resolved before building:
    ERROR   ✗ Entry point not found: 'src/myapp/__main__.py'
    ERROR   ✗ Required packaging file not found: 'packaging/windows/myapp.iss'
    ERROR For details on each requirement, see "Project Compliance" in the
          documentation (In-Depth Guides → Project Compliance).

Compliance rules
================

The table below lists every rule that is evaluated.  Which rules are checked
depends on the ``deployment_mode`` in ``builder.toml`` and the build command
being run.

.. list-table::
   :header-rows: 1
   :widths: 5 45 20 30

   * - #
     - Rule
     - Applies to
     - See also
   * - 1
     - ``pyproject.toml`` must exist at the project root and contain
       ``[project] name`` and ``[project] version``.
     - All commands
     - :ref:`project_layout` — *Project name and version*
   * - 2
     - The source root directory (``src/`` by default, or the value of
       ``[cython] source_root`` in ``builder.toml``) must exist.
     - All build commands
     - :ref:`project_layout` — *Source layout (src/ layout)*,
       :ref:`configuration`
   * - 3
     - The package directory ``{source_root}/{package}/`` must exist.
       The package name is derived from the ``pyproject.toml`` project name
       with hyphens replaced by underscores (e.g. ``my-app`` →
       ``src/my_app/``).
     - All build commands
     - :ref:`project_layout` — *Source layout (src/ layout)*
   * - 4
     - ``{source_root}/{package}/__main__.py`` must exist.  This file is
       used as the application entry point by PyInstaller (``pyinstaller``
       mode) and by the installed console script in all modes.
     - All build commands
     - :ref:`windows_exe`
   * - 5
     - The Windows packaging directory (``packaging/windows/`` by default,
       or the value of ``[windows] script_dir`` in ``builder.toml``) must
       exist.
     - ``build windows``, ``build all`` — *not* ``wheel_only`` mode
     - :ref:`project_layout` — *Windows packaging layout*,
       :ref:`configuration`
   * - 6
     - ``{package}.iss`` must exist in the packaging directory.  This is the
       Inno Setup script that defines the installer contents and metadata.
     - ``build windows``, ``build all`` — *not* ``wheel_only`` mode
     - :ref:`windows_installer`
   * - 7
     - ``{package}_commandline.bat`` must exist in the packaging directory.
       This launcher script is copied into the distribution and lets users
       start the application from a Command Prompt.
     - ``build windows``, ``build all`` — *not* ``wheel_only`` mode
     - :ref:`windows_installer`
   * - 8
     - ``{package}_powershell.ps1`` must exist in the packaging directory.
       This launcher script is copied into the distribution and lets users
       start the application from PowerShell.
     - ``build windows``, ``build all`` — *not* ``wheel_only`` mode
     - :ref:`windows_installer`
   * - 9
     - ``.python-version`` must exist at the project root.  It is the single
       source of truth for the Python version used by the PythonRuntime
       setup script and the offline venv build.  Create the file with the
       target version string on a single line (e.g. ``3.13``).
     - ``build windows``, ``build all`` — ``pyruntime`` mode only
     - :ref:`windows_installer` — *Online and offline installer modes*
   * - 10
     - The project package must be installed in the active virtual
       environment (a dist-info entry discoverable by
       ``importlib.metadata`` must exist).  This is required so that the
       PyInstaller hook can call ``copy_metadata()`` to bundle the package's
       dist-info into the frozen executable, making
       ``importlib.metadata.version()`` work at runtime.  If the check
       fails, run ``uv sync`` (or ``pip install -e .``) and retry.
     - ``build windows``, ``build all``, ``check`` — ``pyinstaller`` mode only
     - :ref:`windows_exe` — *Mode 1: pyinstaller*

.. note::

   Rules 5–10 are only evaluated when the ``deployment_mode`` in
   ``builder.toml`` requires them.  In ``wheel_only`` mode rules 5–9 are
   skipped entirely because no installer is created.  Rule 9 is only
   evaluated in ``pyruntime`` mode.  Rule 10 is only evaluated in
   ``pyinstaller`` mode.

.. note::

   Compliance checking validates *project structure* only.  It does not
   check whether external tools such as PyInstaller, Sphinx, or Inno Setup
   are installed.  Tool availability is verified immediately afterwards by
   the pre-flight checks.  See :ref:`installation` for how to install the
   required tools.

Relationship to pre-flight checks
==================================

``scaldys-builder`` performs two validation phases before any build work
begins:

1. **Compliance check** (this page): confirms that the *project's own files*
   are in place.
2. **Pre-flight check** (:ref:`installation`): confirms that the required
   *external tools* (Sphinx, PyInstaller, Inno Setup) are installed and
   locatable.

Both phases collect all failures before reporting, so you always see the
complete list of problems in a single run rather than discovering them one
at a time.
