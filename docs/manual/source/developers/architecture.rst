.. _architecture:

************
Architecture
************


Architecture Overview
=====================

``scaldys-builder`` is built around **three cooperating responsibilities**:

* **Environment** — discovers tools and paths, runs pre-flight checks.
* **Builder** — orchestrates the high-level pipeline steps.
* **Step classes** (``Compiler``, ``Packager``, ``DocumentationBuilder``) —
  each owns one slice of the work and depends on the environment for shared
  state.

The module layout mirrors this split:

.. code-block:: text

    src/scaldys_builder/
    ├── builder.py              # CLI entry-point (Typer app)
    ├── common/
    │   ├── base.py             # BaseBuildEnvironment, BaseBuilder
    │   ├── compile_runner.py   # Cython/setuptools build script (run as subprocess)
    │   ├── config.py           # builder.toml loading and dataclasses
    │   ├── docs.py             # DocumentationBuilder (Sphinx)
    │   └── utils.py            # Retry-safe file operations
    └── windows/
        └── builder.py          # WindowsBuildEnvironment, Compiler, Packager, WindowsBuilder

The Three-Class Composition Pattern
-------------------------------------

For the Windows platform the composition looks like this:

.. code-block:: text

    WindowsBuilder
    ├── env: WindowsBuildEnvironment   (paths, tool discovery, pre-flight)
    ├── doc_builder: DocumentationBuilder   (Sphinx)
    ├── compiler: Compiler                  (Cython → .pyd, then PyInstaller)
    └── packager: Packager                  (examples, helpers, Inno Setup)

**WindowsBuildEnvironment** (``windows/builder.py``)
    Extends ``BaseBuildEnvironment``.  Adds Windows-specific tool discovery
    (``pyinstaller_exe_path``, ``innosetup_exe_path``), Windows-specific
    directory constants (``script_dir_path``, ``dist_exe_dir_path``, …), and
    a ``pre_flight_checks()`` override that validates PyInstaller and Inno
    Setup are present before any work starts.

**Compiler** (``windows/builder.py``)
    Owns the Cython + PyInstaller sub-pipeline.  ``run_cython()`` stages
    source files, compiles declared modules to ``.pyd``, and excludes their
    ``.py`` originals from the staging area.  ``run_pyinstaller()`` then
    bundles the staged tree into a standalone executable.

**Packager** (``windows/builder.py``)
    Owns the distribution-layout step and installer creation.
    ``prepare_examples()`` and ``prepare_windows_files()`` assemble the final
    directory tree; ``run_innosetup()`` invokes ``ISCC.exe`` to produce the
    ``.exe`` installer.

**DocumentationBuilder** (``common/docs.py``)
    Shared across platforms.  Builds the user guide and optional developer
    guide using ``sphinx-build`` and ``sphinx-apidoc``.

**WindowsBuilder** (``windows/builder.py``)
    Thin orchestrator.  Its ``main()`` method defines an ordered ``steps``
    list and drives the Rich progress bar.  Each step is a ``(label, callable)``
    pair.  Individual step methods (``build_docs``, ``build_exe``,
    ``build_installer``) are also exposed so the CLI can invoke them
    independently.

---