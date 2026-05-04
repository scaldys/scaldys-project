.. _cython_compilation:

******************
Cython Compilation
******************

``scaldys-builder`` can optionally compile selected Python modules to native
Windows extension modules (``.pyd`` files) using Cython and the MSVC compiler.
This is useful for two purposes:

- **Performance** — tight inner loops or CPU-intensive code can run
  significantly faster as native extensions.
- **Obfuscation** — compiled ``.pyd`` files do not ship as readable Python
  source, making it harder to inspect business logic or algorithms.

When to use Cython compilation
================================

Cython compilation is entirely optional.  If ``compiled_modules`` is empty
(the default), ``scaldys-builder`` stages the Python source tree as-is for
PyInstaller.  Enable it only for modules where the trade-offs are worth the
added complexity:

- Modules that are on hot paths and have been profiled as bottlenecks.
- Modules that contain proprietary algorithms you do not wish to ship as
  plain source.

Requirements
============

Install the ``[cython]`` extra::

    uv add --dev "scaldys-builder[cython]"

This installs ``Cython`` and ``setuptools``.  The MSVC compiler must also be
present; it is provided by *Visual Studio Build Tools* or a full Visual Studio
installation.  The CPython installer does not include a C compiler.

Configuration
=============

Declare modules to compile in ``builder.toml``:

.. code-block:: toml

    [cython]
    compiled_modules = [
        "myapp.core.engine",
        "myapp.core.crypto",
    ]
    source_root = "src"          # default; omit if your layout uses "src/"

Each entry is a fully-qualified dotted module path, exactly as you would
write it in an ``import`` statement.

How it works
============

The compilation runs as part of ``scaldys-builder build windows exe``.
Internally it proceeds in three phases:

Phase 1 — Source staging
-------------------------

The entire source tree under ``source_root`` is copied to
``build/compiled/``.  This staging directory becomes the working tree for
both Cython and PyInstaller, leaving your original source untouched.

.. code-block:: text

    src/myapp/              →   build/compiled/myapp/
        __init__.py                 __init__.py
        core/                       core/
            engine.py                   engine.py   ← will be compiled
            utils.py                    utils.py    ← kept as-is
            crypto.py                   crypto.py   ← will be compiled

Phase 2 — Cython compilation
-----------------------------

``scaldys-builder`` invokes its internal compile runner as a subprocess::

    python -P -m scaldys_builder.common.compile_runner \
        build/compiled  myapp.core.engine myapp.core.crypto

The runner uses ``Cython.Build.cythonize`` with ``setuptools`` to:

1. Generate C source files from the ``.py`` files (e.g. ``engine.c``).
2. Compile the C sources with MSVC to produce ``.pyd`` files
   (e.g. ``engine.cpython-313-win_amd64.pyd``).
3. Remove the intermediate ``.c`` files.

Phase 3 — Source clean-up
--------------------------

After compilation, ``scaldys-builder`` removes the ``.py`` files in
``build/compiled/`` that correspond to compiled modules.  This ensures
PyInstaller picks up the ``.pyd`` extension rather than the Python source:

.. code-block:: text

    build/compiled/myapp/core/
        engine.cpython-313-win_amd64.pyd   ← compiled extension
        engine.py                          ← REMOVED
        crypto.cpython-313-win_amd64.pyd   ← compiled extension
        crypto.py                          ← REMOVED
        utils.py                           ← kept (not in compiled_modules)

Limitations and caveats
========================

MSVC required
-------------

Cython-generated C extensions on Windows must be compiled with the same
compiler used to build CPython itself — MSVC.  If ``cl.exe`` is not on
``PATH`` (typically via a *Developer Command Prompt* or the Visual Studio
environment), compilation will fail with a compiler-not-found error.

Not all Python is valid Cython
------------------------------

Pure-Python files compile with Cython without any changes in most cases.
However, some dynamic Python patterns (heavy use of ``exec``, ``eval``,
runtime ``__import__``, etc.) may behave differently or fail to compile.
Test compiled modules carefully before shipping.

Module dependencies
-------------------

Only the modules listed in ``compiled_modules`` are compiled.  Modules that
import compiled modules work normally — the Python import system resolves
``.pyd`` files just like ``.py`` files.

Debugging compiled modules
--------------------------

Stack traces from compiled modules show the original Python source line
numbers (Cython embeds them).  However, you cannot set breakpoints directly
in a ``.pyd`` file with standard Python debuggers.  Keep the original source
available during development and compile only for release builds.
