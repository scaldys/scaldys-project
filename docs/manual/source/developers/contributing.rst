.. _contributing:

************
Contributing
************

This guide explains the internal architecture of ``scaldys-builder`` and
describes the extension points you need to know when adding new functionality.

.. contents:: On this page
   :local:
   :depth: 2

---

Development Setup
=================

Clone the repository and create the virtual environment with `uv
<https://docs.astral.sh/uv/>`_::

    git clone https://github.com/scaldys/scaldys-builder.git
    cd scaldys-builder
    uv sync --group dev

This installs the package in editable mode together with all development
dependencies (pytest, ruff, pyright, Sphinx, etc.).

Running the Tests
-----------------

::

    uv run pytest

With coverage::

    uv run pytest --cov=scaldys_builder --cov-report=term-missing

Linting and Type Checking
--------------------------

::

    uv run ruff check src tests
    uv run ruff format src tests
    uv run pyright

Building the Documentation Locally
------------------------------------

::

    uv run sphinx-build -b html docs/manual/source docs/manual/build/html

Or via the convenience wrapper::

    cd docs/manual && make html

Versioning, Building, and Publishing
--------------------------------------

Version is declared once in ``pyproject.toml`` under ``[project] version`` and
read at runtime via ``importlib.metadata`` in
``src/scaldys_builder/__about__.py``.  Update ``pyproject.toml`` before
tagging a release.

Build a wheel and source distribution::

    uv build

Publish to PyPI (requires a configured API token)::

    uv publish

To test against TestPyPI first, uncomment the ``[[tool.uv.index]]`` block in
``pyproject.toml`` and run::

    uv publish --index testpypi

Consuming a Local Development Version
--------------------------------------

While iterating, point a consuming project directly at the local source tree
without publishing::

    # From inside the consuming project
    uv add --dev "scaldys-builder @ path/to/scaldys-builder"

Or install in editable mode so changes are reflected immediately::

    uv add --dev --editable "path/to/scaldys-builder"

---

Extension Points
================

Adding a New Cython Module to a Consuming Project
--------------------------------------------------

Compiled modules are declared in the consuming project's ``builder.toml``,
not in ``scaldys-builder`` itself.  To add a module:

1. Add the dotted module name to the ``compiled_modules`` list::

       [cython]
       compiled_modules = ["mypackage.hot_path", "mypackage.parser"]

2. ``Compiler.run_cython()`` reads this list at build time and passes it to
   ``compile_runner.py`` via ``setup()`` → ``cythonize()``.  No changes to
   ``scaldys-builder`` are needed.

The ``source_root`` key (default ``src``) tells the compiler where your
package lives relative to the project root::

    [cython]
    source_root = "src"
    compiled_modules = ["mypackage.fast_module"]

See :ref:`configuration` for the full ``builder.toml`` reference.

Adding a New Build Step to ``WindowsBuilder.main()``
-----------------------------------------------------

``main()`` keeps its pipeline in a plain list of ``(description, callable)``
pairs (``windows/builder.py``, the ``steps`` variable inside ``main()``):

.. code-block:: python

    steps = [
        ("Pre-flight checks", lambda: self.env.pre_flight_checks(...)),
        ("Cleaning build directories", self.clean),
        ("Building documentation", self.build_docs),
        ("Building executable", self.build_exe),
        ("Building installer", self.build_installer),
    ]

To insert a new step:

1. Implement the logic as a method on ``WindowsBuilder`` (or delegate to a
   new helper class that holds a reference to ``self.env``).
2. Append or insert a ``(label, self.new_step)`` tuple in the ``steps`` list
   at the appropriate position.
3. If the step requires an external tool, add a corresponding
   ``require_<tool>=True`` kwarg to the ``pre_flight_checks()`` call at the
   top of ``steps``, and teach ``WindowsBuildEnvironment.pre_flight_checks()``
   to validate it.

Adding a New Platform Builder
------------------------------

``scaldys-builder`` is designed so that a Linux or macOS builder can be added
without touching existing Windows code.  You need four things:

1. **A new** ``BuildEnvironment`` subclass
   Create ``src/scaldys_builder/<platform>/builder.py`` and subclass
   ``BaseBuildEnvironment``::

       from scaldys_builder.common.base import BaseBuildEnvironment

       class LinuxBuildEnvironment(BaseBuildEnvironment):
           def __init__(self, project_path: Path, verbose: bool = False) -> None:
               super().__init__(project_path, verbose)
               # Discover platform-specific tools here
               self.appimage_tool_path = self._find_tool("appimagetool", ...)

           def pre_flight_checks(self, **kwargs: Any) -> None:
               # Validate platform-specific tools
               ...

2. **A new** ``Builder`` subclass
   In the same file, subclass ``BaseBuilder``::

       from scaldys_builder.common.base import BaseBuilder

       class LinuxBuilder(BaseBuilder):
           def __init__(self, project_path: Path, verbose: bool = False) -> None:
               env = LinuxBuildEnvironment(project_path, verbose)
               super().__init__(env)
               self.env: LinuxBuildEnvironment = env  # narrow type
               self.doc_builder = DocumentationBuilder(self.env)
               # Add platform-specific step classes as needed

           def main(self) -> None:
               steps = [...]  # Same pattern as WindowsBuilder.main()
               ...

3. **Wire up CLI commands** in ``builder.py``
   Add a new ``Typer`` sub-app following the existing pattern::

       from scaldys_builder.linux.builder import LinuxBuilder

       linux_app = typer.Typer(help="Linux specific build subcommands", no_args_is_help=True)
       build_app.add_typer(linux_app, name="linux")

       @linux_app.command("all")
       def linux_all(verbose: bool = ...) -> None:
           builder = LinuxBuilder(PROJECT_ROOT, verbose=verbose)
           builder.main()

4. **Add a** ``BuildEnvironment`` **dataclass if needed**
   If the new platform requires configuration keys beyond what ``builder.toml``
   already provides, extend ``common/config.py`` with a new section dataclass
   and register it on ``BuildConfig``.

---

Reporting Issues
================

Please report bugs and feature requests on the GitHub issue tracker:

https://github.com/scaldys/scaldys-builder/issues
