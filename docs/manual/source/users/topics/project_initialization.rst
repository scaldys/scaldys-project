.. _project_initialization:

**********************
Project Initialisation
**********************

``scaldys-project init`` scaffolds a new project from the
`scaldys-template <https://github.com/scaldys/scaldys-template>`_ repository.
It downloads the template, collects project metadata through an interactive
wizard, and performs all file renaming and string substitution in one step —
producing a ready-to-use project directory with a working virtual environment
and (optionally) an initial git commit.

This is the recommended starting point for any new scaldys-compliant project.

----

What the command does
=====================

At a high level, ``scaldys-project init`` performs these operations in order:

1. **Collects parameters** — an interactive wizard prompts for project name,
   package name, author, description, and other metadata.
2. **Acquires the template** — downloads the ``scaldys-template`` ZIP archive
   from GitHub, or copies a local directory if ``--local`` is supplied.
3. **Copies a filtered tree** — excludes runtime and IDE artefacts that should
   not be part of a new project (see :ref:`excluded_items`).
4. **Replaces placeholder strings** — substitutes every occurrence of the
   template's placeholder names in all text files (see :ref:`substitution_map`).
5. **Renames files and directories** — renames every path component that still
   contains a placeholder string.
6. **Applies targeted post-processing** — corrects the copyright year in Sphinx
   ``conf.py`` files, the description and version in ``pyproject.toml``, and the
   deployment mode in ``scaldys-project.toml``.
7. **Runs post-init actions** (optional) — ``git init`` with an initial commit
   and ``uv sync`` to create the virtual environment.

----

The interactive wizard
======================

Running ``scaldys-project init`` with no flags launches a four-section wizard.
Each prompt shows a default value in brackets; press **Enter** to accept it.

Project identity
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Prompt
     - Notes
   * - **Project name**
     - The human-readable display name used in CLI help text, documentation
       titles, and the installer.  Example: ``My Cool App``.
   * - **Package name**
     - The Python import name.  Default: project name lowercased with spaces
       and hyphens replaced by underscores.  Example: ``my_cool_app``.
   * - **Project slug**
     - The CLI command name and file-name prefix.  Default: project name
       lowercased with spaces and underscores replaced by hyphens.
       Example: ``my-cool-app``.
   * - **Organization name**
     - Used as the top-level folder inside the OS app-data directory
       (e.g. ``%LOCALAPPDATA%\<Organization>\<Package>`` on Windows).
       Default: ``Scaldys``.

Author & metadata
-----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Prompt
     - Notes
   * - **Author name**
     - Written to ``pyproject.toml`` and Sphinx ``conf.py``.
   * - **Author email**
     - Written to ``pyproject.toml``.
   * - **Short description**
     - One-line project description for ``pyproject.toml``.
       Default: ``A Python application.``
   * - **Initial version**
     - Starting version number.  Default: ``0.1.0``.
   * - **GitHub username/org**
     - Optional.  When provided, badge and link URLs in ``README.md`` are
       updated from ``github.com/scaldys/`` to ``github.com/<username>/``.
       Leave empty to skip.

Build configuration
-------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Prompt
     - Notes
   * - **Deployment mode**
     - Selects the Windows packaging strategy written to
       ``scaldys-project.toml``.  Choices: ``wheel_only`` (default),
       ``pyinstaller``, ``pyruntime``.  See :ref:`windows_exe` for details.

Output & post-init actions
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Prompt
     - Notes
   * - **Target directory**
     - Where to create the new project.  Relative paths are resolved from the
       current working directory.  Default: ``./<project-slug>``.
   * - **Initialise git repository?**
     - When ``Y``, runs ``git init`` and makes an initial commit.  Default:
       ``Y``.  Required for ``scaldys-project ci markdown`` to work (pre-commit
       needs a git repository).
   * - **Run uv sync?**
     - When ``Y``, runs ``uv sync`` to install all dependencies and create the
       project-local ``.venv``.  Default: ``Y``.

After all values are collected a summary panel is shown.  Confirm with **Y**
to proceed; press **N** to abort without creating any files.

----

.. _substitution_map:

Placeholder substitution
========================

The template uses four distinct placeholder strings.  They are substituted
in a fixed order so that no partial match can corrupt another replacement:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Find
     - Replace with
     - Where it appears
   * - ``Scaldys-Template``
     - *project name*
     - CLI help text, Sphinx doc titles, installer display name
   * - ``scaldys_template``
     - *package name*
     - Python import paths, ``pyproject.toml``, Sphinx ``conf.py``
   * - ``scaldys-template``
     - *project slug*
     - CLI entry-point name, file names, Inno Setup script
   * - ``scaldys@scaldys.net``
     - *author email*
     - ``pyproject.toml`` author block
   * - ``Scaldys``
     - *organization name*
     - ``__about__.py``, app-data path construction
   * - ``github.com/scaldys/``
     - ``github.com/<github_username>/``
     - README badge URLs *(only when GitHub username is provided)*

Binary files (identified by extension or failed UTF-8 decoding) are skipped
for content replacement.  Only their names are updated where applicable.

----

.. _excluded_items:

What is excluded
================

The following items from the template are **not** copied into the new project:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Item
     - Reason
   * - ``.git/``
     - Git history is not transferred; a fresh repo is created instead.
   * - ``.idea/``
     - IDE-specific files; each developer generates their own.
   * - ``build/``
     - Compiled artefacts; rebuilt on first run.
   * - ``app_data/``
     - Runtime state (settings file, log); created at first application run.
   * - ``dist/``, ``artifacts/``
     - Distribution artefacts; generated by ``scaldys-project build``.
   * - ``uv.lock``
     - Regenerated fresh by ``uv sync`` with current dependency versions.
   * - ``__pycache__/``, ``*.egg-info``
     - Python byte-code caches and package metadata; rebuilt automatically.

----

Using a local template copy
============================

If you have a local clone of ``scaldys-template`` (for example a fork or a
version not yet pushed to GitHub), pass it with ``--local``::

    scaldys-project init --local ../scaldys-template

The command uses that directory as the template source instead of downloading
from GitHub.  The same exclusion list and substitution logic applies.

To pin to a specific GitHub branch or tag without using a local copy, pass
``--template-ref``::

    scaldys-project init --template-ref v1.2.0

----

Overwriting an existing directory
==================================

If the target directory already exists the command aborts with an error.  To
overwrite it add ``--force``::

    scaldys-project init --force

.. note::
   ``--force`` permanently deletes the existing directory before creating the
   new project.  There is no undo.  Use it only when you intentionally want
   to re-scaffold the directory.

----

Running commands in the new project
=====================================

After ``cd``-ing into the new project directory, use ``uv run`` to invoke
``scaldys-project`` commands.  This ensures the project-local ``.venv`` is
used regardless of any other virtual environment that may be activated in the
shell::

    cd my-cool-app
    uv run scaldys-project check
    uv run scaldys-project ci all

Alternatively, activate the project's own virtual environment first and then
run commands directly::

    .\.venv\Scripts\Activate.ps1    # Windows PowerShell
    scaldys-project check

.. tip::
   If ``scaldys-project check`` reports that the package is not installed in
   the active virtual environment, you are running it with a different venv
   than the one ``uv sync`` created inside the new project.  Use ``uv run``
   or activate ``.venv`` first.

----

CLI options reference
=====================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--local PATH``
     - Use a local directory as the template source instead of downloading
       from GitHub.
   * - ``--template-ref REF``
     - Branch or tag of ``scaldys-template`` to download.  Default:
       ``master``.  Example: ``--template-ref v1.0.0``.
   * - ``--force``, ``-f``
     - Overwrite the target directory if it already exists.
   * - ``--no-git``
     - Skip ``git init`` and the initial commit.
   * - ``--no-sync``
     - Skip running ``uv sync`` after the project is created.
   * - ``--help``
     - Show command help and exit.

For the complete ``init`` command entry in the CLI reference see
:ref:`cli_init`.
