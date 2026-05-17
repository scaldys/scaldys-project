.. _scaldys_toml_reference:

****************************
scaldys.toml — Full Reference
****************************

The annotated file below lists every available ``scaldys.toml`` setting in
one place.  Each option is accompanied by an inline comment that describes
its purpose, accepted values, and default.  Copy this block into your project
root, adjust the values to suit your project, and delete any comments or
sections you do not need.

For narrative explanations of each section see :ref:`configuration`.

.. code-block:: toml

    # scaldys.toml — complete annotated reference
    #
    # Place this file alongside pyproject.toml in your project root.
    # Every setting has a default, so the file is entirely optional —
    # pure-Python projects with packaging files in the default locations
    # require no configuration at all.
    # ──────────────────────────────────────────────────────────────────────────


    # ══════════════════════════════════════════════════════════════════════════
    # [cython] — Cython compilation settings
    # ══════════════════════════════════════════════════════════════════════════
    #
    # Controls whether selected Python modules are compiled to native Windows
    # extension (.pyd) files before PyInstaller bundles the application.
    # Cython compilation serves two purposes:
    #
    #   1. Performance  — tight inner loops and numerical code can be 2–10×
    #                     faster than the equivalent pure-Python bytecode.
    #   2. Obfuscation  — compiled .pyd files do not expose Python source,
    #                     making proprietary algorithms harder to reverse-engineer.
    #
    # If the [cython] section is omitted entirely, all defaults below apply and
    # no Cython compilation is performed.

    [cython]

    # compiled_modules
    #
    # A list of fully-qualified, dotted module paths to compile with Cython.
    # Each entry must resolve to a .py file under `source_root`.  The builder
    # runs cythonize() on each listed module, produces a .pyd extension, and
    # stages everything (compiled and uncompiled alike) under build/compiled/
    # before handing the tree to PyInstaller.
    #
    # Example:
    #   compiled_modules = [
    #       "myapp.core.engine",   # performance-critical inner loop
    #       "myapp.core.crypto",   # obfuscation: hide algorithm details
    #   ]
    #
    # Default: [] — Cython is disabled; all source files are staged as-is.
    compiled_modules = []

    # source_root
    #
    # Directory (relative to the project root) that contains the top-level
    # Python source packages.
    #
    #   src-layout project  →  source_root = "src"   (default)
    #   flat-layout project →  source_root = "."  or  source_root = "mypackage"
    #
    # Default: "src"
    source_root = "src"


    # ══════════════════════════════════════════════════════════════════════════
    # [docs] — Documentation build settings
    # ══════════════════════════════════════════════════════════════════════════
    #
    # Controls which documentation units are processed by `build docs`,
    # which of those are distributed alongside the Windows application, and
    # which require a sphinx-apidoc pre-pass to auto-generate API reference
    # stubs.
    #
    # A "documentation unit" is a subdirectory of docs/ that contains its own
    # Sphinx source tree (i.e. a source/conf.py file), for example:
    #   docs/manual/
    #   docs/developer_guide/
    #
    # If the [docs] section is omitted entirely, all defaults below apply.

    [docs]

    # public_doc_dirs
    #
    # A list of subdirectory names under docs/ whose built HTML output is
    # copied into the distribution artefacts after a successful
    # `build windows` (or `build all`) run.  These are the
    # documentation units destined for end users of the program.
    #
    # For each name listed, the builder copies:
    #   build/<name>/html/  →  dist/portable/documentation/<name>/
    #   build/<name>/html/  →  dist/documentation/<name>/
    #
    # The first tree is picked up by the Inno Setup script and bundled inside
    # the Windows setup.exe, making the documentation available to end-users
    # offline after installation.  The second tree provides a standalone
    # documentation-only copy that can be distributed independently of the
    # portable package.  An empty list builds all documentation units but
    # ships none of them with the installer.
    #
    # Example:
    #   public_doc_dirs = ["manual"]
    #
    # Default: [] — no documentation is distributed with the installer.
    public_doc_dirs = []

    # internal_doc_dirs
    #
    # A list of subdirectory names under docs/ that contain internal
    # documentation for the developers of the program — information that
    # explains how the software works internally, and which is not distributed
    # to end users.
    #
    # For each name listed, `sphinx-apidoc` is run automatically before
    # `sphinx-build`.  sphinx-apidoc scans the Python source tree and generates
    # .rst stub files for every public module, producing an API reference
    # section from docstrings.  Only include units that actually require the
    # sphinx-apidoc pre-pass; purely hand-authored internal units do not need
    # it and should be omitted.  Must be a subset of the Sphinx directories
    # (i.e. those that have a source/conf.py file).
    #
    # Example:
    #   internal_doc_dirs = ["developer_guide"]
    #
    # Default: [] — no sphinx-apidoc pre-pass; all .rst files are hand-authored.
    internal_doc_dirs = []


    # ══════════════════════════════════════════════════════════════════════════
    # [windows] — Windows packaging settings
    # ══════════════════════════════════════════════════════════════════════════
    #
    # Controls the Windows distribution pipeline: where the packaging files
    # live and whether the installer targets offline or online deployment.
    #
    # This section is consumed by `build windows` and `build all`.
    # In pyinstaller and pyruntime modes, the following files must exist inside
    # script_dir, named after the project (hyphens replaced by underscores):
    #
    #   {project_name}.iss                 Inno Setup script       (required)
    #   {project_name}_commandline.bat     command-line launcher   (required)
    #   {project_name}_powershell.ps1      PowerShell launcher     (required)
    #   setup_pyruntime.ps1                runtime setup script    (required in pyruntime mode)
    #   {project_name}.ico                 application icon        (optional)
    #
    # In wheel_only mode none of the above files are required.
    #
    # If the [windows] section is omitted entirely, all defaults below apply.

    [windows]

    # script_dir
    #
    # Directory (relative to the project root) containing the Windows packaging
    # files listed above.  The builder reads launcher scripts from here, copies
    # them into the distribution tree, and passes the .iss script to Inno
    # Setup's ISCC compiler.
    #
    # Default: "packaging/windows"
    script_dir = "packaging/windows"

    # deployment_mode
    #
    # Controls how the application is packaged for Windows users.
    # Three values are supported:
    #
    # "pyinstaller" (default)
    #   PyInstaller bundles the application into a self-contained executable
    #   directory (dist/portable/bin/).  Inno Setup wraps it into a setup .exe.
    #   No Python installation is required on the end-user's machine.
    #
    # "pyruntime"
    #   PyInstaller is NOT used.  The installer deploys a managed Python virtual
    #   environment (PythonRuntime) into the installation directory.  Launcher
    #   scripts activate that environment rather than calling a frozen executable.
    #   Use this mode when the application must coexist with tools such as Quarto
    #   or Jupyter that require a real Python interpreter.
    #   Requires .python-version at the project root.
    #
    # "wheel_only"
    #   Builds only a binary distribution wheel.  No Windows installer is
    #   created.  Use this for packages distributed via pip or uv rather than a
    #   setup .exe.  The .iss script and launcher files are not required.
    #
    # Default: "pyinstaller"
    deployment_mode = "pyinstaller"

    # bundle_pyruntime
    #
    # Only meaningful when deployment_mode = "pyruntime".
    # Selects between online and offline installer sub-modes.
    #
    # false (default) — ONLINE mode
    #   uv.exe is staged in the bin/ directory of the distribution.  During
    #   installation, setup_pyruntime.ps1 uses uv to download and create the
    #   PythonRuntime virtual environment on the end-user's machine.
    #   The resulting setup.exe is significantly smaller.
    #
    # true            — OFFLINE mode
    #   A complete PythonRuntime virtual environment is pre-built at
    #   dist/pyruntime/ during the build itself (using uv).  Its path is then
    #   passed to Inno Setup via the /DPythonRuntimeDir preprocessor define,
    #   and the entire environment is embedded inside setup.exe.
    #   No internet access is needed on the end-user's machine at install time.
    #
    #   Prerequisites for offline mode:
    #     - A .python-version file must exist at the project root (single line,
    #       e.g. "3.13") specifying which Python version to install.
    #     - uv must be available on PATH at build time.
    #
    # Default: false
    bundle_pyruntime = false
