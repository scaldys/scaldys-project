.. _configuration:

*************
Configuration
*************

``scaldys-builder`` reads project-specific build settings from a
``builder.toml`` file in the project root.  Every setting has a default, so
the file is entirely optional — pure-Python projects with packaging files in
the default location require no configuration at all.

File location
=============

Place ``builder.toml`` alongside ``pyproject.toml`` in your project root::

    my-project/
        pyproject.toml
        builder.toml        ← optional
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

Controls which documentation units are distributed and which require a
``sphinx-apidoc`` pre-pass.

.. code-block:: toml

    [docs]
    dist_dirs = ["manual"]
    apidoc_dirs = ["developer_guide"]

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Key
     - Default
     - Description
   * - ``dist_dirs``
     - ``[]``
     - List of subdirectory names under ``docs/`` whose built HTML output
       (``build/<name>/html/``) is copied into the distribution artefacts
       (``dist/pyinstaller/documentation/<name>/``).  An empty list means
       no documentation is distributed.
   * - ``apidoc_dirs``
     - ``[]``
     - List of subdirectory names that require a ``sphinx-apidoc`` pre-pass
       before ``sphinx-build`` is invoked.  Must be a subset of the Sphinx
       directories (those containing ``source/conf.py``).

**Example — distribute one unit, generate one unit from source code**

.. code-block:: toml

    [docs]
    dist_dirs = ["manual"]
    apidoc_dirs = ["developer_guide"]

See :ref:`documentation_building` for a full explanation of how the doc
build works.

``[windows]``
-------------

Controls Windows-specific packaging paths.

.. code-block:: toml

    [windows]
    script_dir = "packaging/windows"

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

    [docs]
    dist_dirs = ["manual"]
    apidoc_dirs = ["developer_guide"]

Defaults summary
================

If ``builder.toml`` is absent, or a section / key is missing, the following
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
   * - ``docs.dist_dirs``
     - ``[]`` (no documentation distributed)
   * - ``docs.apidoc_dirs``
     - ``[]`` (no apidoc pre-pass)
