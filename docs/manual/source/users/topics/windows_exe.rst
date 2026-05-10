.. _windows_exe:

*******************************
PyInstaller Executable Bundling
*******************************

``scaldys-builder build windows exe`` uses PyInstaller to package your Python
project into a self-contained Windows application directory.  No Python
installation is required on the end-user's machine.

Requirements
============

Install the ``[windows]`` extra::

    uv add --dev "scaldys-builder[windows]"

This installs ``PyInstaller``.

How it works
============

The bundling step follows the Cython compilation step (see
:ref:`cython_compilation`).  If Cython compilation is disabled, PyInstaller
bundles directly from the original source tree.

PyInstaller is called programmatically with a fixed set of options that have
been tuned for Windows distribution:

One-directory bundle (``--onedir``)
-----------------------------------

PyInstaller is run in *one-directory* mode: it produces a folder containing
the executable and all required libraries rather than a single merged
``exe``.  This avoids the slow startup time of a one-file build and makes
antivirus software less likely to flag the executable during extraction.

.. code-block:: text

    dist/pyinstaller/
        bin/
            myapp.exe           ← launcher executable
            python313.dll
            _internal/         ← all imported packages and DLLs

Console mode
------------

The executable is built as a *console application* (``--console``) so that
``stdout`` / ``stderr`` output from your application is visible in a terminal
or can be redirected.  If your application is a pure GUI application that
should suppress the console window, this would need to be changed in a
future configuration option.

UPX disabled
------------

UPX compression is explicitly disabled (``--noupx``).  UPX-compressed
binaries are frequently flagged as suspicious by antivirus software because
compression is a technique also used by malware packers.  Skipping UPX
produces larger executables but avoids false positives.

Module collection
-----------------

PyInstaller is instructed to ``--collect-submodules`` for your top-level
package.  This ensures that dynamically-imported submodules (e.g. plugins
loaded via ``importlib``) are included in the bundle even if PyInstaller's
static analysis does not detect the imports.

Hook file handling
------------------

PyInstaller uses *hook files* (``hook-<package>.py``) to describe how to
bundle packages with special requirements.  ``scaldys-builder`` renames any
hook file in your packaging directory from
``hook-<project_name>.py`` to ``hook-<package_name>.py`` so that PyInstaller
discovers it correctly regardless of naming conventions in your project.

Icon support
------------

If an ``<project_name>.ico`` file is found in the packaging directory
(``[windows] script_dir``), it is passed to PyInstaller via ``--icon`` and
embedded in the executable.


Output location
===============

.. code-block:: text

    dist/
        pyinstaller/
            bin/
                myapp.exe
                python313.dll
                ...
                wheels/
                    myapp-1.2.3-cp313-cp313-win_amd64.whl   ← distribution wheel

The ``build windows installer`` step copies launcher scripts and
documentation into ``dist/pyinstaller/`` before creating the final installer.

Distribution wheel
==================

After PyInstaller completes, ``scaldys-builder`` automatically builds a
``.pyd``-only distribution wheel from the compiled staging area
(``build/compiled/``).  This wheel contains compiled ``.pyd`` extension
modules only — no Python source files — which protects proprietary algorithm
details while still making the full package importable in a Python environment.

The wheel is placed in ``dist/pyinstaller/bin/wheels/`` where Inno Setup
can bundle it into the installer and the PythonRuntime setup script
(``setup_pyruntime.ps1``) can install it via
``uv pip install --find-links <wheels_dir>``.

How the wheel is built
----------------------

1. A copy of the project's ``pyproject.toml`` is written into
   ``build/compiled/`` so that setuptools can discover the package.
2. The copy is patched to:

   - restrict package discovery to the project package only (excluding
     ``extra_hooks/`` and other top-level directories), and
   - declare ``*.pyd`` files as package data so that setuptools includes the
     compiled extensions in the wheel.

3. ``uv build --wheel`` is invoked from ``build/compiled/`` and the resulting
   ``.whl`` file is moved to ``dist/pyinstaller/bin/wheels/``.

.. note::

   The wheel build requires ``uv`` to be available on ``PATH``.  ``uv`` is
   already used throughout the rest of the build pipeline, so no additional
   installation is needed.  If ``uv`` is not found, the step raises an error
   and the build fails.

.. note::

   The wheel build is only meaningful when Cython compilation is enabled
   (``[cython] compiled_modules`` is non-empty in ``builder.toml``).  If no
   modules are compiled, the staged ``build/compiled/`` tree contains plain
   Python source and the resulting wheel is equivalent to a regular sdist wheel
   with no source-protection benefit.

Build directories
=================

PyInstaller's intermediate working files are written to
``build/pyinstaller/`` and are separate from the final output.  The
``build windows clean`` command removes this directory along with all other
build artefacts.

.. code-block:: text

    build/
        pyinstaller/    ← PyInstaller work directory (intermediate)

Common issues
=============

Missing modules at runtime
--------------------------

PyInstaller analyses import statements statically.  Dynamic imports
(``__import__(name)``, ``importlib.import_module(name)`` with a variable
``name``) are not detected automatically.  Use the
``--collect-submodules`` flag (which ``scaldys-builder`` already passes for
your top-level package) or add hidden imports to your hook file:

.. code-block:: python

    # hook-myapp.py
    hiddenimports = ["myapp.plugins.pdf", "myapp.plugins.csv"]

Antivirus false positives
-------------------------

Some antivirus products flag PyInstaller executables.  ``scaldys-builder``
already disables UPX to reduce the likelihood of this.  If false positives
persist, consider signing the executable with a code-signing certificate.

Large bundle size
-----------------

PyInstaller includes every imported package.  Audit your dependencies and
remove unused ones.  The ``--exclude-module`` option can be added to a hook
file to exclude known-unnecessary packages (e.g. ``tkinter``, ``unittest``).
