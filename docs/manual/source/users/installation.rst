.. _installation:

Installation
============

Requirements
------------

- Python 3.13 or newer
- `uv <https://docs.astral.sh/uv/>`_ (recommended) or ``pip``
- Windows (for the ``build windows`` commands; the tool itself installs on any platform)

Installing as a development dependency
---------------------------------------

``scaldys-builder`` is a build-time tool and should be added as a development
dependency of your project, not a runtime dependency.

With **uv** (recommended)::

    uv add --dev scaldys-builder

With **pip**::

    pip install --index-url https://pypi.org/simple/ scaldys-builder

Optional extras
---------------

The core package installs only the CLI framework and Rich console output.
Install the extras for the build features you need:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Extra
     - What it adds
     - Install command
   * - ``cython``
     - Cython and setuptools for compiling Python modules to ``.pyd``
     - ``uv add --dev "scaldys-builder[cython]"``
   * - ``windows``
     - PyInstaller for bundling a standalone Windows executable
     - ``uv add --dev "scaldys-builder[windows]"``
   * - ``docs``
     - Sphinx and the RTD theme for building HTML documentation
     - ``uv add --dev "scaldys-builder[docs]"``

To install all extras at once::

    uv add --dev "scaldys-builder[cython,windows,docs]"

Using a local development version
-----------------------------------

While iterating on the library itself, point a consuming project directly at
the local source tree::

    uv add --dev "scaldys-builder @ path/to/scaldys-builder"

Or install in editable mode so changes are reflected immediately without
reinstalling::

    uv add --dev --editable "path/to/scaldys-builder"

Verifying the installation
---------------------------

After installation the ``scaldys-builder`` script is available in your
environment::

    scaldys-builder --help

You should see the top-level help message listing the available subcommands.

External tool dependencies
---------------------------

Some build steps rely on external tools that must be installed separately and
available on ``PATH`` (or in their standard installation locations):

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Tool
     - Required for
     - Notes
   * - Sphinx (``sphinx-build``)
     - ``build windows docs``
     - Installed via the ``[docs]`` extra
   * - PyInstaller (``pyinstaller``)
     - ``build windows exe``
     - Installed via the ``[windows]`` extra
   * - Inno Setup (``ISCC.exe``)
     - ``build windows installer``
     - Download from `jrsoftware.org <https://jrsoftware.org/isinfo.php>`_;
       must be installed to the default ``%ProgramFiles%`` location or be on
       ``PATH``

The ``build windows all`` command performs pre-flight checks before starting
and reports clearly which tools are missing.
