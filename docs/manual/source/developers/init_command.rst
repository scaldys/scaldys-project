.. _init_command_internals:

****************************
init Command — Internals
****************************

This page describes the internal design of ``scaldys-project init``
(``src/scaldys_project/cli/commands/cmd_init.py``).  It is intended for
contributors who need to maintain or extend the command.

For the user-facing guide see :ref:`project_initialization`.

----

Overview
========

``init`` is a **self-contained command** — unlike the build commands it does
not instantiate ``WindowsBuilder`` or use ``find_project_root()``, because it
operates on a directory that does not yet exist.  All file-system work is done
through stdlib modules only: ``pathlib``, ``shutil``, ``tempfile``,
``zipfile``, ``urllib.request``, ``subprocess``, ``datetime``, and ``re``.
No new package-level dependencies are introduced.

The command is registered as a single top-level command in ``cli/cli.py``::

    app.command("init")(cmd_init.init)

----

Module structure
================

The module is organised as a set of private helper functions called in sequence
by the public ``init()`` entry point.

.. code-block:: text

    cmd_init.py
    │
    ├── _to_package_name(s)            slug helper: "My App" → "my_app"
    ├── _to_project_slug(s)            slug helper: "My App" → "my-app"
    │
    ├── _collect_params()              interactive wizard → dict[str, Any]
    ├── _print_summary(params)         Rich panel before confirmation
    │
    ├── _download_template(ref, tmp)   GitHub ZIP → extracted root Path
    ├── _copy_filtered(src, dst)       copy tree, skipping excluded items
    │
    ├── _build_replacements(params)    ordered list of (find, replace) pairs
    ├── _is_binary(path)               detect files to skip for text replacement
    ├── _replace_in_file(path, repls)  apply replacements to one text file
    ├── _replace_content(root, repls)  walk tree, call _replace_in_file on each
    │
    ├── _rename_component(name, ...)   apply name substitutions to one path component
    ├── _rename_paths(root, ...)       post-order rename of all matching paths
    │
    ├── _post_process(root, params)    targeted fixes: conf.py, pyproject.toml, sp.toml
    ├── _run_post_init(dir, git, sync) git init + commit, uv sync
    │
    └── init(...)                      CLI entry point — orchestrates the above

----

Template acquisition
====================

When ``--local`` is not provided the command downloads a ZIP archive from
GitHub::

    https://github.com/scaldys/scaldys-template/archive/refs/heads/<ref>.zip

If that URL fails (e.g. for a tag), it retries with::

    https://github.com/scaldys/scaldys-template/archive/refs/tags/<ref>.zip

The archive is extracted into a ``tempfile.mkdtemp()`` directory.  GitHub's
ZIP format always places all files inside a single root folder named
``<repo>-<ref>/``; ``_download_template`` strips that root and returns the
inner directory as the template source path.

The caller (``init()``) wraps the entire processing block in a ``try/finally``
that calls ``shutil.rmtree(tmp_dir, ignore_errors=True)`` to guarantee cleanup
even if an exception aborts the process.

When ``--local PATH`` is provided, ``local`` is used directly as
``template_src`` and no temporary directory is created or cleaned up.

----

Exclusion list
==============

``_copy_filtered`` skips the following during the copy phase:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Pattern
     - Matched by
   * - ``.git``, ``.idea``, ``build``, ``app_data``, ``dist``, ``artifacts``, ``__pycache__``
     - ``_EXCLUDE_NAMES`` frozenset — exact directory/file name match
   * - ``uv.lock``
     - ``_EXCLUDE_EXACT`` frozenset — exact file name match
   * - ``*.egg-info``
     - ``_EXCLUDE_SUFFIXES`` tuple — ``name.endswith()`` check

The function recurses through the source tree and creates the corresponding
subtree in ``dst``, skipping any entry (directory or file) whose name matches
the exclusion rules.

----

.. _replacement_ordering:

Replacement ordering
=====================

``_build_replacements()`` returns a fixed-order list of ``(find, replace)``
pairs.  The ordering is **critical**: each pattern must be substituted before
any pattern of which it is a sub-string.

.. list-table::
   :header-rows: 1
   :widths: 5 25 25 45

   * - #
     - Find
     - Replace with
     - Why this position
   * - 1
     - ``Scaldys-Template``
     - *project name*
     - Contains ``Scaldys``; must be replaced before the bare ``Scaldys`` pattern
       at position 5.
   * - 2
     - ``scaldys_template``
     - *package name*
     - Underscored form — distinct from the hyphenated form; order relative to
       position 3 is not strictly required, but kept for clarity.
   * - 3
     - ``scaldys-template``
     - *project slug*
     - Hyphenated form — does not overlap with position 2.
   * - 4
     - ``scaldys@scaldys.net``
     - *author email*
     - Specific string; placed before the bare ``Scaldys`` replacement so the
       domain ``scaldys.net`` is not corrupted first.
   * - 5
     - ``Scaldys``
     - *organization name*
     - Most general; placed last among the core replacements.
   * - 6
     - ``github.com/scaldys/``
     - ``github.com/<github_username>/``
     - Appended conditionally — only when the user provides a GitHub username.

All replacements are **case-sensitive** plain string operations (``str.replace``),
applied in order to the full text of each file.

----

Binary file detection
=====================

``_is_binary(path)`` returns ``True`` (skip content replacement) if:

1. The file's suffix (lowercased) is in ``_BINARY_EXTENSIONS``:
   ``.ico``, ``.png``, ``.jpg``, ``.jpeg``, ``.gif``, ``.bmp``,
   ``.exe``, ``.dll``, ``.pyd``, ``.whl``, ``.zip``, ``.tar``.
2. Attempting to decode the first 1 024 bytes of the file as UTF-8 raises
   ``UnicodeDecodeError``.

Binary files are still renamed (their path component may contain a placeholder
string); only their *contents* are left unchanged.

----

Path renaming
=============

``_rename_paths()`` renames every file and directory whose name contains
``scaldys_template`` or ``scaldys-template``.

The rename walk uses a **post-order strategy**: all paths are sorted by depth
(``len(path.parts)``) in descending order, so the deepest entries are renamed
first.  This ensures that a directory rename does not invalidate the recorded
path of a child that has not yet been renamed.

Each path is checked with ``path.exists()`` before renaming because a parent
directory may have already been renamed (moving the child to a new path).

The replacement is performed by ``_rename_component(name, package_name,
project_slug)``, which applies the two name substitutions in order:
``scaldys_template`` → ``package_name``, then ``scaldys-template`` →
``project_slug``.

----

Targeted post-processing
=========================

After generic content replacement and path renaming, ``_post_process()``
applies three targeted fixes that cannot be expressed as simple string
substitutions.

Sphinx ``conf.py`` — copyright year and author
-----------------------------------------------

Generic replacement transforms ``"2024-2026, scaldys_template"`` into
``"2024-2026, <package_name>"``.  ``_post_process`` then applies two regex
and string operations to every ``conf.py`` found under ``docs/``:

1. **Copyright year**: ``re.sub`` replaces
   ``copyright = "<year>-<year>, <package_name>"`` with
   ``copyright = "<current_year>, <author_name>"``.
   ``datetime.date.today().year`` is used for the current year.

2. **Author field**: ``str.replace`` substitutes
   ``author = "<package_name>"`` with ``author = "<author_name>"``.

If ``author_name`` was left blank by the user, ``package_name`` is used as a
fallback so the field is never empty.

``pyproject.toml`` — description and version
---------------------------------------------

Generic replacement cannot distinguish the placeholder description
(``"A skeleton for Python projects by Scaldys."``) from any other string that
happens to contain ``Scaldys``.  ``_post_process`` performs a literal
``str.replace`` targeting the exact placeholder text, replacing it with the
user-supplied description.

The template version ``"0.9.0"`` is replaced via ``re.sub`` with a
``MULTILINE`` flag, targeting the ``version = "0.9.0"`` line specifically.

``scaldys-project.toml`` — deployment mode
-------------------------------------------

When the user selects a deployment mode other than the default ``pyinstaller``,
a literal ``str.replace`` updates the ``deployment_mode`` value.  No action is
taken when the default is kept.

----

Error handling and cleanup
==========================

Partial output cleanup
----------------------

If a ``typer.Exit`` exception is raised during the processing phase (e.g. a
missing ``--local`` path, or a download failure), the ``except typer.Exit``
block removes the partially-created target directory before re-raising.  This
leaves the filesystem in a clean state rather than stranding an incomplete
project.

Post-init failures are non-fatal
---------------------------------

``_run_post_init()`` treats both ``git`` and ``uv sync`` failures as warnings
rather than errors.  The project files are fully created before these steps
run, so a failure (e.g. ``git`` not on ``PATH``, or a network error during
``uv sync``) does not invalidate the project.  A yellow warning message directs
the user to run the failed step manually.

Force overwrite
---------------

When ``--force`` is supplied and the target directory already exists,
``shutil.rmtree(target_dir)`` removes it entirely *before* the processing
phase begins.  The removal happens unconditionally once ``--force`` is
confirmed — there is no additional safety prompt.

----

Extending the command
=====================

Adding a new wizard prompt
--------------------------

1. Add the ``typer.prompt()`` or ``typer.confirm()`` call inside
   ``_collect_params()`` and include the result in the returned ``dict``.
2. If the value maps to a string substitution, add a new ``(find, replace)``
   pair to ``_build_replacements()`` — observe the :ref:`replacement_ordering`
   rules when choosing the insertion position.
3. If the value requires a targeted fix (non-string operation), add a block
   to ``_post_process()``.
4. Update the summary table in ``_print_summary()`` and the documentation in
   :ref:`project_initialization`.

Adding a new exclusion
----------------------

* Exact name matches (directory or file): add to ``_EXCLUDE_NAMES`` or
  ``_EXCLUDE_EXACT``.
* Suffix matches: add to ``_EXCLUDE_SUFFIXES``.
* Binary file extensions (skip content replacement only, not copy): add to
  ``_BINARY_EXTENSIONS``.

Changing the template source
-----------------------------

The GitHub URL constants are defined at module level::

    _GITHUB_ZIP_HEADS = "https://github.com/scaldys/scaldys-template/archive/refs/heads/{ref}.zip"
    _GITHUB_ZIP_TAGS  = "https://github.com/scaldys/scaldys-template/archive/refs/tags/{ref}.zip"

To point ``init`` at a different template repository, update these two
constants.  No other changes are required.
