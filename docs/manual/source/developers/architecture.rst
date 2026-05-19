.. _architecture:

************
Architecture
************


``scaldys-project`` is built around **three cooperating responsibilities**:

* **Environment** — discovers tools and paths, runs pre-flight checks.
* **Builder** — orchestrates the high-level pipeline steps.
* **Step classes** (``Compiler``, ``Packager``, ``DocumentationBuilder``) —
  each owns one slice of the work and depends on the environment for shared
  state.

The module layout mirrors this split:

.. code-block:: text

    src/scaldys_project/
    ├── __main__.py             # minimal entry point — imports app from cli/
    ├── cli/
    │   ├── cli.py              # Typer app, logging setup, command wiring
    │   ├── utils.py            # shared Console instance, find_project_root()
    │   └── commands/
    │       ├── cmd_build.py    # build subcommands (all, docs, windows, clean)
    │       ├── cmd_check.py    # check command
    │       ├── cmd_ci.py       # ci subcommands (all, lint, format, typecheck, build)
    │       └── cmd_test.py     # test command
    ├── common/
    │   ├── base.py             # BaseBuildEnvironment, BaseBuilder
    │   ├── compile_runner.py   # Cython/setuptools build script (run as subprocess)
    │   ├── config.py           # scaldys-project.toml loading and dataclasses
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
    Shared across platforms.  Builds all documentation units found under
    ``docs/`` using ``sphinx-build``.

**WindowsBuilder** (``windows/builder.py``)
    Thin orchestrator.  Its ``main()`` method defines an ordered ``steps``
    list and drives the Rich progress bar.  Each step is a ``(label, callable)``
    pair.  Individual step methods (``build_docs``, ``build_exe``,
    ``build_installer``) are also exposed so the CLI can invoke them
    independently.


Execution Flow
--------------

Tracing what happens when ``scaldys-project build all`` is run:

1. **Module load** — ``__main__.py`` is the minimal entry point; it imports
   ``app`` from ``cli/cli.py``, which sets up logging and wires all command
   modules.  When the ``build_all`` command is invoked, ``find_project_root()``
   (from ``cli/utils.py``) walks up from ``cwd`` until it finds a
   ``pyproject.toml`` file.

2. **Builder instantiation** — the ``build_all`` command function calls
   ``WindowsBuilder(find_project_root(), verbose=verbose)``.  The constructor chain:

   a. ``WindowsBuilder.__init__`` creates a ``WindowsBuildEnvironment``.
   b. ``WindowsBuildEnvironment.__init__`` calls ``super().__init__()``
      (``BaseBuildEnvironment``), which reads ``pyproject.toml`` for ``name``
      and ``version``, calls ``load_config()`` to read ``scaldys-project.toml``, and
      discovers shared tools (``sphinx-build``).
   c. Back in ``WindowsBuildEnvironment``, Windows-specific tools are
      discovered (``pyinstaller.exe``, ``ISCC.exe``) and Windows-specific
      paths are resolved from the loaded config.
   d. ``WindowsBuilder.__init__`` then creates the three step objects:
      ``DocumentationBuilder(env)``, ``Compiler(env)``, ``Packager(env)``.

3. **Pipeline execution** — ``builder.main(console=console)`` assembles the
   ``steps`` list (via ``_distribution_steps(require_sphinx=True)``) and
   drives a Rich progress bar through each entry in order.  The step list is
   mode-dependent:

   .. code-block:: python

       steps = [
           ("Checking project compliance", ...),
           ("Pre-flight checks",           lambda: self.env.pre_flight_checks(...)),
           ("Cleaning build directories",  self.clean),
           ("Building documentation",      self.build_docs),
           ("Building distribution",       self.build_exe),     # Cython + wheel (+ PyInstaller in Mode 1)
           # ("Building installer", self.build_installer),      # omitted in wheel_only mode
       ]

   Any exception raised by a step aborts the pipeline and surfaces the error
   via the Rich console.

4. **Individual commands** — ``build docs`` and ``build windows`` each
   instantiate ``WindowsBuilder``, call ``env.pre_flight_checks()`` with
   the specific tool flags they need, and invoke the appropriate step methods
   directly, bypassing the full pipeline.  ``build clean`` calls
   ``builder.clean()`` directly.


Configuration Loading
---------------------

``common/config.py`` provides the single ``load_config(project_path)``
function.  It is called once inside ``BaseBuildEnvironment.__init__`` and its
result is stored as ``self.config``.

.. code-block:: text

    scaldys-project.toml  ──▶  load_config()  ──▶  BuildConfig
                                              ├── cython: CythonConfig
                                              │       compiled_modules: list[str]
                                              │       source_root: str
                                              ├── docs: DocsConfig
                                              │       public_doc_dirs: list[str]
                                              └── windows: WindowsConfig
                                                      script_dir: str
                                                      deployment_mode: str
                                                      bundle_pyruntime: bool

If ``scaldys-project.toml`` is absent ``load_config()`` returns ``BuildConfig()``
immediately, applying all dataclass defaults.  If the file is present,
``tomllib`` parses it and each section is mapped to the corresponding
dataclass; any missing key falls back to its dataclass default.

The config object is accessed throughout the codebase via ``self.env.config``
(for step classes) or ``self.config`` (inside ``BaseBuildEnvironment``
subclasses).  No component re-reads the file at runtime — the single load at
construction time is the authoritative source.


Why *compile_runner.py* Runs as a Subprocess
-----------------------------------------------

``setuptools.setup()`` is designed to be called once as the main entry point
of a script.  It reads directly from ``sys.argv``, modifies global
``distutils`` and ``sys.modules`` state, and is not safe to call from inside
a long-running process.  Invoking it inside the parent ``scaldys-project``
process would corrupt its ``sys.argv`` and import state.

Running it as a subprocess solves this cleanly::

    python -P -m scaldys_project.common.compile_runner build_ext \
        --build-lib <path> --compiler=msvc

The child process receives a controlled ``sys.argv``, starts with a clean
import state, and exits after ``setup()`` completes — leaving the parent
process unaffected.

The ``-P`` flag additionally prevents Python from prepending the current
working directory to ``sys.path``, so only installed packages and the staging
directory influence the build, regardless of what the parent process has on
its path.

The deferred Cython import in ``compile_runner.py`` (inside the
``if __name__ == "__main__":`` block) is a direct consequence of this design:
the module can be safely scanned by import tools and test runners without
requiring the ``[cython]`` extra to be installed.

---

To extend the system with new modules, build steps, or a new platform builder,
see :ref:`extension_points`.  For the contributor workflow (cloning, testing,
publishing), see :ref:`contributing`.
