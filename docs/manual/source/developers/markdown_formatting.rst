.. _markdown_formatting_guide:

*****************************
Markdown Formatting and Hooks
*****************************

This page explains the full picture of Markdown formatting in this project:
why Prettier is used, how the pre-commit configuration is split between a
project-level file and a config bundled in the ``scaldys-project`` wheel,
and what happens at each stage — git commit, local CLI command, and GitHub
Actions CI.

.. contents:: On this page
   :local:
   :depth: 2


Why Prettier for Markdown?
==========================

Python tooling (ruff, pyright) handles Python source files, but leaves
Markdown untouched.  Markdown files in this project — ``README.md``,
``licenses/*.md``, and documentation pages — benefit from the same kind of
automated, deterministic formatting:

* **Consistent line wrapping** — long paragraphs are reflowed to a fixed print
  width, making diffs easier to read and review.
* **Uniform blank lines and spacing** — heading separators, list indentation,
  and fenced code blocks are normalised automatically.
* **No manual style debates** — the formatter decides; contributors follow.

`Prettier <https://prettier.io/>`_ is the de-facto standard formatter for
Markdown.  It is managed here through the ``pre-commit`` framework so that
Node.js does **not** need to be installed by contributors — pre-commit
downloads and isolates Prettier automatically.


``.prettierrc``
===============

.. code-block:: json

    {
      "printWidth": 80,
      "proseWrap": "always",
      "endOfLine": "auto"
    }

``printWidth: 80``
    Paragraphs are reflowed so that no line exceeds 80 characters.

``proseWrap: "always"``
    Prettier actively wraps prose to ``printWidth``.  Without this option
    Prettier would leave existing long lines untouched.

``endOfLine: "auto"``
    Prettier preserves whatever line endings are already in the file rather
    than enforcing LF.  This prevents a conflict with Git's ``core.autocrlf``
    setting on Windows: without ``"auto"``, Prettier would rewrite CRLF files
    to LF, Git would convert them back to CRLF, and every commit would
    trigger a spurious "files were modified by this hook" failure.


Pre-commit Configuration Files
================================

Two pre-commit configurations are involved in Markdown formatting.  They are
almost identical — same repository mirror, same pinned version, same
file-type filter — but differ in one critical flag:

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Config
     - Prettier flag
     - Used by
   * - ``.pre-commit-config.yaml`` *(project file)*
     - *(none — rewrite mode)*
     - git pre-commit hook, ``format markdown``, GitHub Actions
   * - ``scaldys_project/resources/.pre-commit-check-config.yaml`` *(bundled in wheel)*
     - ``--check``
     - ``ci markdown``

``.pre-commit-config.yaml`` — rewrite mode (project file)
----------------------------------------------------------

.. code-block:: yaml

    repos:
      - repo: https://github.com/rbubley/mirrors-prettier
        rev: v3.8.3
        hooks:
          - id: prettier
            types_or: [markdown]

This file lives at the root of each scaldys-compliant project.  When invoked
without ``--check``, Prettier **rewrites files in place**.  pre-commit detects
that files were modified and exits non-zero, printing
``files were modified by this hook``.  This is the expected behaviour for a
git pre-commit hook: the commit is blocked, the files are already fixed, and
the contributor simply runs ``git add`` and retries the commit.

This config is also used by ``scaldys-project format markdown`` (where the
intent is explicitly to apply fixes) and by the GitHub Actions ``ci.yml``
workflow step.

``.pre-commit-check-config.yaml`` — check-only mode (bundled in wheel)
------------------------------------------------------------------------

.. code-block:: yaml

    repos:
      - repo: https://github.com/rbubley/mirrors-prettier
        rev: v3.8.3
        hooks:
          - id: prettier
            args: ["--check"]
            types_or: [markdown]

With ``--check``, Prettier reads each file and compares it to what it would
produce.  If any file differs, it **prints the file names and exits non-zero,
but does not modify any file**.  This is the behaviour needed for a
verification command: report what is wrong without silently changing the
working tree.

This config is owned entirely by the ``scaldys-project`` tool — its content
is identical in every consuming project — so it is bundled as a package
resource inside the wheel
(``scaldys_project/resources/.pre-commit-check-config.yaml``).  When
``scaldys-project ci markdown`` runs, the command resolves the absolute path
to the bundled file via ``importlib.resources`` and passes it to pre-commit's
``--config`` flag.  **No** ``.pre-commit-check-config.yaml`` file is required
in the consuming project.

Why not a single config file?
------------------------------

Ruff provides a dedicated ``--diff`` flag for check-only mode, so a single
command suffices (``ruff format --diff .`` vs ``ruff format .``).  Prettier
has no equivalent CLI flag that can be injected at invocation time when
running through pre-commit — the ``args`` list must be declared in the
configuration file.  A second configuration file is therefore the cleanest
way to toggle between rewrite mode and check-only mode without modifying the
shared ``.pre-commit-config.yaml`` that governs the git hook.  Bundling the
check-only config in the wheel removes it as a file that consumer projects
must maintain.

Maintenance note
    When upgrading Prettier, update the ``rev`` field in ``.pre-commit-config.yaml``
    *and* in ``src/scaldys_project/resources/.pre-commit-check-config.yaml``
    inside the ``scaldys-project`` source tree, and keep ``types_or`` in sync.
    The only intentional difference between the two configs is the presence or
    absence of ``args: ["--check"]``.


The ``ci`` vs ``format`` Command Contract
==========================================

All ``scaldys-project ci`` commands are **check-only**: they detect problems
and exit non-zero, but they never modify files.  This mirrors GitHub Actions
exactly — CI detects failures; it does not auto-fix and commit.

All ``scaldys-project format`` commands are **fix-in-place**: they rewrite
files and exit with the formatter's return code.

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Command
     - Modifies files?
     - Underlying invocation
   * - ``ci format``
     - No
     - ``uv run ruff format --diff .``
   * - ``ci markdown``
     - No
     - ``uv run pre-commit run --config <bundled-check-config> prettier --all-files``
   * - ``format python``
     - Yes
     - ``uv run ruff format .``
   * - ``format markdown``
     - Yes
     - ``uv run pre-commit run prettier --all-files``

The intended local workflow is:

1. Run ``scaldys-project ci all`` to check everything — same result as CI.
2. If ``ci format`` fails, run ``scaldys-project format python`` to fix.
3. If ``ci markdown`` fails, run ``scaldys-project format markdown`` to fix.
4. Stage and commit the fixed files.
5. Run ``scaldys-project ci all`` again to confirm everything is clean.


Local vs GitHub Actions Behaviour
===================================

Understanding exactly what happens in each environment prevents confusion.

On a git commit (local)
------------------------

When ``uv run pre-commit install`` has been run, the git pre-commit hook
fires on every ``git commit``.  It uses ``.pre-commit-config.yaml`` (rewrite
mode).

* If all Markdown files are already correctly formatted: hook exits ``0``,
  commit proceeds.
* If any file needs formatting: Prettier rewrites the file(s) in place,
  pre-commit exits non-zero with ``files were modified by this hook``, and
  the commit is **blocked**.  The fixed files are already on disk; the
  contributor runs ``git add -p`` and retries.

``scaldys-project ci markdown`` (local)
-----------------------------------------

Uses the check-only config bundled in the ``scaldys-project`` wheel
(``--check`` mode).  No ``.pre-commit-check-config.yaml`` file is needed in
the project.

* All files correctly formatted: exits ``0``.
* Any file needs formatting: prints the offending file names, exits non-zero.
  **No files are modified.**  Run ``scaldys-project format markdown`` to fix.

``scaldys-project format markdown`` (local)
--------------------------------------------

Uses ``.pre-commit-config.yaml`` (rewrite mode).

* All files correctly formatted: exits ``0``.
* Any file needs formatting: Prettier rewrites the file(s) in place,
  pre-commit exits non-zero.  Stage and commit the changes.

GitHub Actions ``ci.yml``
--------------------------

The workflow step is::

    - name: Prettier format
      run: uv run pre-commit run prettier --all-files

This uses ``.pre-commit-config.yaml`` — the same rewrite-mode config as the
git hook and ``format markdown``.  In CI, Prettier may rewrite files, and
pre-commit exits non-zero to signal that.  Because the CI runner is ephemeral
and does not commit back to the repository, the net effect is identical to a
check: the step fails if any file is not correctly formatted.

The practical guarantee is: **if** ``scaldys-project ci markdown`` **passes
locally, the GitHub Actions step will pass too** — both verify the same
Prettier version, the same ``.prettierrc`` options, and the same set of
files.

Why the GitHub Actions step uses rewrite mode
   Prettier does not expose a ``--check``-only mode through the pre-commit
   hook interface without an ``args`` override in a config file.  The CI step
   uses the project's ``.pre-commit-config.yaml`` (rewrite mode) and relies
   on pre-commit's non-zero exit to fail the pipeline — the runner is
   ephemeral and never commits rewrites back, so the net effect is identical
   to a check.  Switching to the bundled check-only config would require the
   workflow to invoke ``scaldys-project ci markdown`` instead of calling
   pre-commit directly; the current approach is simpler and the outcome is
   identical.


``rbubley/mirrors-prettier`` vs the Official Mirror
=====================================================

The official ``pre-commit/mirrors-prettier`` repository is archived and its
last published release is an alpha.  ``rbubley/mirrors-prettier`` is the
actively maintained community fork that tracks Prettier stable releases.
Both work identically; the fork is used because it receives timely version
tags for new Prettier releases.

The first time the hook runs, pre-commit downloads the pinned Prettier
version into its own isolated cache (``~/.cache/pre-commit/``).  No global
``npm install`` or Node.js setup is required.  Subsequent runs use the
cached binary.
