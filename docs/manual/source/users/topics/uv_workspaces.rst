.. _uv_workspaces:

*************
uv Workspaces
*************

``scaldys-project`` can build the members of a
`uv workspace <https://docs.astral.sh/uv/concepts/projects/workspaces/>`_:
one repository with several projects that depend on each other, such as
shared libraries plus the applications built on them.  Every member keeps
its own version and its own build output, and every application member
produces its own installer.

A project that is not part of a workspace behaves exactly as before.

Layout
======

A workspace has a root ``pyproject.toml`` with a ``[tool.uv.workspace]``
table.  The root is usually *virtual*: it has no ``[project]`` table and is
not built itself.  Each member is a normal scaldys-project project, with its
own ``src/``, ``tests/``, ``docs/`` and ``packaging/`` folders::

    my-workspace/
        pyproject.toml              ← [tool.uv.workspace], root dev group
        .python-version             ← shared by all members
        scaldys-project.toml        ← optional workspace-wide defaults
        uv.lock
        packages/
            store/                  ← library (wheel_only)
                pyproject.toml
                scaldys-project.toml
                src/store/
                tests/
            report/                 ← library, depends on store
                ...
            app/                    ← application (pyinstaller), depends on both
                pyproject.toml
                scaldys-project.toml
                src/app/__main__.py
                tests/
                docs/
                packaging/windows/

The root ``pyproject.toml``:

.. code-block:: toml

    [tool.uv.workspace]
    members = ["packages/*"]
    exclude = ["packages/experimental-*"]

    [tool.uv.sources]
    store = { workspace = true }
    report = { workspace = true }
    app = { workspace = true }

    [dependency-groups]
    dev = ["store", "report", "app", "scaldys-project", "pyinstaller", "pytest", "pytest-cov"]

    [tool.ruff]
    extend-exclude = ["**/build", "**/dist", "**/artifacts"]

The ``members`` globs select the member directories (only those that contain
a ``pyproject.toml``); ``exclude`` globs remove members again.  A project
inside the tree that is excluded is treated as a standalone project.

``build/``, ``dist/``, ``artifacts/``, ``docs/`` and ``packaging/`` stay per
member.  Nothing about a member's own layout changes.

Selecting targets
=================

``build`` (all subcommands), ``check``, ``test`` and ``publish`` accept two
options:

.. option:: --package NAME, -p NAME

   Act on the named member.  Repeatable.  Names are matched like uv does
   (case-insensitive; ``-``, ``_`` and ``.`` are equivalent).

.. option:: --all-packages

   Act on every member.

Members always run in *topological order*: a library comes before the
members that depend on it, whatever order you give on the command line.
The run stops at the first failure.  With more than one target, each one is
introduced by a header.  A summary table with the package, its version and
its result is always printed at the end, also for a single target and after
a failure (see :ref:`cli_summary`).

Without either option:

- inside a member (or any folder below it), the command acts on that member;
- at a virtual workspace root, the command fails with a message that lists
  the members;
- outside a workspace, the command acts on the project, as before.
  ``--package`` and ``--all-packages`` are an error there.

Examples::

    # From the workspace root
    uv run scaldys-project build all --all-packages
    uv run scaldys-project check -p store
    uv run scaldys-project build windows -p app

    # From inside a member
    cd packages/report
    uv run scaldys-project build all

``ci`` and ``format`` always run once at the workspace root, wherever you
start them, so ruff and mdformat check the whole repository:

- ``ci typecheck`` runs ``uv sync --all-packages`` (a bare ``uv sync`` in a
  member would uninstall the other members), then ``pyright``.  When the root
  ``pyproject.toml`` has a ``[tool.pyright]`` table, its ``include`` decides
  what is checked.  Otherwise each member's source root and ``tests/`` are
  passed explicitly.
- ``ci doclint`` runs ``sphinx-lint`` on the root ``docs/`` and on every
  member's ``docs/``.
- ``ci markdown`` / ``format markdown`` use the root ``[format]`` settings
  and the root ``.github/workflows/ci.yml``.

``test`` runs ``uv run --package <member> pytest <member>/tests`` at the
workspace root for each selected member.  At a virtual root with no member
selected, it runs ``uv run pytest`` once at the root, which uses the root
``[tool.pytest.ini_options] testpaths``.

``init`` refuses to run inside an existing workspace.

Root defaults
=============

``.python-version`` and ``scaldys-project.toml`` can live at the workspace
root:

- **.python-version** — a member uses its own file if it has one, otherwise
  the root's.
- **scaldys-project.toml** — the root file provides defaults.  A member's file
  is merged over it section by section, key by key: a key set in the member
  wins, any other key comes from the root.  Paths (``source_root``,
  ``script_dir``) stay relative to the member.
- **[format]** is workspace-wide and is read from the root file only.  Its
  paths are relative to the root.

Example: the root sets ``[docs] public_doc_dirs = ["manual"]`` and
``[cython] source_root = "src"`` for everyone; each member only sets its
``[windows] deployment_mode``.

Internal dependencies and constraints
=====================================

A member's dependency is *internal* when it names another member and has a
``{ workspace = true }`` source, in the member's own ``[tool.uv.sources]`` or
in the root's:

.. code-block:: toml

    # packages/app/pyproject.toml
    [project]
    name = "app"
    version = "1.4.0"
    dependencies = ["store>=0.3", "report>=0.2", "rich>=15"]

Versions stay independent.  ``check`` (and every build) validates the
constraints against the members' current versions:

- a constraint the dependency's version does not meet (``store>=0.3`` while
  ``store`` is ``0.2.1``) is a compliance error;
- an internal dependency without a constraint gives a warning, because the
  published wheel would accept any version.

A dependency cycle between members is an error.

The wheel of every member is built from the staged ``build/compiled/`` tree
with ``tool.uv.sources``, ``tool.uv.workspace`` and ``tool.uv.index``
removed from the staged ``pyproject.toml`` and with ``uv build --no-sources``.
A member's wheel therefore declares ``store>=0.3`` like any published
package, with no reference to the workspace.

Libraries, the members with ``deployment_mode = "wheel_only"``, do not need
a ``__main__.py``.

Application members that bundle libraries
=========================================

When ``build all`` or ``build windows`` runs on a member that is **not**
``wheel_only`` and has internal dependencies, an extra step,
*Building internal dependencies*, runs after the clean step.  For each
member in the app's internal closure (direct and indirect, libraries first)
it:

1. runs that member's own clean, Cython staging and wheel build, so the
   member's own ``compiled_modules`` apply;
2. copies the wheel into the app's ``build/internal_wheels/``.  Not into
   ``dist/``: ``publish`` refuses a ``dist/`` with more than one binary
   wheel.

Within one command run, each member is built only once.  With
``--all-packages`` the libraries are built first as targets of their own, and
the apps reuse those wheels.

What happens next depends on the app's deployment mode:

``pyinstaller``
    For each internal dependency PyInstaller gets:

    - ``--paths <dep>/build/compiled``, ahead of the app's own, so the
      staged (possibly Cython-compiled) copy wins over the editable install;
    - ``--collect-submodules <dep_package>``, because plugins that load
      through entry points are invisible to PyInstaller's import analysis;
    - ``--copy-metadata <dep>``, which also carries ``entry_points.txt`` so
      ``importlib.metadata.entry_points()`` and ``version()`` work in the
      frozen executable;
    - ``--additional-hooks-dir <dep>/packaging/hooks`` when that folder
      exists, for the dependency's data files.

    ``--copy-metadata`` needs the dependencies installed in the active
    environment.  The compliance check reports a missing one and suggests
    ``uv sync --all-packages``.

``pyruntime``
    The internal wheels are copied next to the app wheel in
    ``artifacts/portable/wheels/``.  In offline mode
    (``bundle_pyruntime = true``) the PythonRuntime install adds
    ``--find-links build/internal_wheels``.  In online mode the app's
    ``setup_pyruntime.ps1`` must install from the bundled ``wheels/`` folder
    (``uv pip install --find-links <bin>\..\wheels <app>``), because the
    internal libraries are not on any index.

A member without a ``docs/`` folder skips the documentation step of
``build all`` with an info message.

The "bundle" app pattern
------------------------

An app member can exist only to ship several libraries as one installer.
For example, ``my-suite`` depends on ``store`` and ``report`` and provides
the command-line entry point that discovers them as plugins:

.. code-block:: toml

    # packages/my-suite/pyproject.toml
    [project]
    name = "my-suite"
    version = "2.0.0"
    dependencies = ["store>=0.3", "report>=0.2"]

    [tool.uv.sources]
    store = { workspace = true }
    report = { workspace = true }

.. code-block:: toml

    # packages/my-suite/scaldys-project.toml
    [windows]
    deployment_mode = "pyinstaller"
    exe_name = "suite"

``report`` registers itself through an entry point
(``[project.entry-points."suite.plugins"]``), and ``my-suite`` finds it at
runtime with ``importlib.metadata.entry_points(group="suite.plugins")``.
That works in the frozen ``suite.exe`` because of ``--collect-submodules``
and ``--copy-metadata`` above.  Mark such a member
``Private :: Do Not Upload`` if it should never reach PyPI.

The root dev group pattern
==========================

Put every member, ``scaldys-project`` and the build tools into the root
``dev`` dependency group (see the layout example above).  Then a plain
``uv sync`` at the root installs all members editable into the one shared
``.venv``.  This matters for two reasons:

- ``uv sync --package <member>`` (or ``uv sync`` inside a member, without
  such a group) uninstalls the other members, which breaks ``--copy-metadata``
  for apps that bundle them;
- ``uv run scaldys-project …`` then works from the root and from every
  member.

Publishing
==========

``publish --all-packages`` publishes the members in topological order, so a
library reaches the index before the apps that require it.  Members with the
``Private :: Do Not Upload`` classifier are skipped with a notice.  The
pure-binary-wheel check applies to each member's ``dist/`` separately.
