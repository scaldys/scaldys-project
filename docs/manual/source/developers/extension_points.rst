.. _extension_points:

****************
Extension Points
****************

This page describes how to extend ``scaldys-project`` — either by configuring
new behaviour from a consuming project, or by modifying the codebase itself.

Before reading this page, the :ref:`architecture` page provides the structural
context that makes the extension points below easier to follow.

.. contents:: On this page
   :local:
   :depth: 2


Design Conventions
==================

Understanding these patterns before modifying the code prevents accidentally
breaking the design:

- **Three-class composition, not inheritance.**  Each platform has an
  ``Environment`` class (paths + tool discovery), one or more step classes
  (``Compiler``, ``Packager``), and a thin ``Builder`` orchestrator.  Logic
  is added to the appropriate class, not to the orchestrator.

- **Steps list as data.**  ``WindowsBuilder.main()`` keeps its pipeline as a
  plain ``list`` of ``(label, callable)`` pairs.  This makes the sequence
  explicit and easy to extend without subclassing.

- **Config is loaded once.**  ``load_config()`` is called inside
  ``BaseBuildEnvironment.__init__`` and stored as ``self.config``.  No
  component re-reads ``builder.toml`` at runtime.  Extend ``config.py`` if
  new configuration keys are needed.

- **Platform code stays in its subdirectory.**  Windows-specific logic lives
  entirely inside ``windows/builder.py``.  Shared logic (base classes, config,
  docs, utils) lives in ``common/``.  Adding a new platform means adding a
  new ``<platform>/`` directory without touching existing code.

- **External tools are validated early.**  ``pre_flight_checks()`` is always
  the first step in the pipeline.  New steps that require external tools must
  add the corresponding validation there, not inline.


Adding a New Cython Module to a Consuming Project
==================================================

Compiled modules are declared in the consuming project's ``builder.toml``,
not in ``scaldys-project`` itself.  To add a module:

1. Add the dotted module name to the ``compiled_modules`` list::

       [cython]
       compiled_modules = ["mypackage.hot_path", "mypackage.parser"]

2. ``Compiler.run_cython()`` reads this list at build time and passes it to
   ``compile_runner.py`` via ``setup()`` → ``cythonize()``.  No changes to
   ``scaldys-project`` are needed.

The ``source_root`` key (default ``src``) tells the compiler where your
package lives relative to the project root::

    [cython]
    source_root = "src"
    compiled_modules = ["mypackage.fast_module"]

See :ref:`configuration` for the full ``builder.toml`` reference.


Adding a New Build Step to ``WindowsBuilder.main()``
=====================================================

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
==============================

``scaldys-project`` is designed so that a Linux or macOS builder can be added
without touching existing Windows code.  You need four things:

1. **A new** ``BuildEnvironment`` subclass
   Create ``src/scaldys_project/<platform>/builder.py`` and subclass
   ``BaseBuildEnvironment``::

       from scaldys_project.common.base import BaseBuildEnvironment

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

       from scaldys_project.common.base import BaseBuilder

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

3. **Wire up CLI commands** in ``__main__.py``
   Add a new ``Typer`` sub-app following the existing pattern::

       from scaldys_project.linux.builder import LinuxBuilder

       linux_app = typer.Typer(help="Linux specific build subcommands", no_args_is_help=True)
       build_app.add_typer(linux_app, name="linux")

       @linux_app.command("all")
       def linux_all(verbose: bool = ...) -> None:
           builder = LinuxBuilder(PROJECT_ROOT, verbose=verbose)
           builder.main()

4. **Add a** ``BuildConfig`` **section if needed**
   If the new platform requires configuration keys beyond what ``builder.toml``
   already provides, extend ``common/config.py`` with a new section dataclass
   and register it on ``BuildConfig``.

---

For the contributor workflow (cloning, testing, publishing), see
:ref:`contributing`.
