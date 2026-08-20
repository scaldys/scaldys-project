.. _markdown_formatting_guide:

*****************************
Markdown Formatting and Tools
*****************************

This page explains how Markdown formatting works in ``scaldys-project``:
why ``mdformat`` is used directly via ``uv``, how target files are scoped
(``README.md`` and MkDocs documentation in ``docs/``), and what happens at
each stage — local CLI commands and GitHub Actions CI.

.. contents:: On this page
   :local:
   :depth: 2


Why mdformat for Markdown?
==========================

Python tools such as Ruff and Pyright handle Python source files, but leave
Markdown untouched.  Markdown files in a project — such as ``README.md`` and
user-facing documentation pages — benefit from automated, deterministic
formatting:

* **Pure-Python toolchain** — ``mdformat`` is written in Python and runs directly
  via ``uv run mdformat`` without requiring Node.js, npm, or wrapper frameworks
  like ``pre-commit``.
* **CommonMark compliance** — ``mdformat`` enforces standard CommonMark formatting,
  producing clean, predictable Markdown syntax across all platforms.
* **Consistent diffs** — list numbering, code block fences, indentation, and blank
  lines are formatted deterministically.
* **Unified developer experience** — Markdown checking and formatting work with
  the exact same CLI idioms (``ci`` and ``format``) as Ruff and Pyright.


Target File Scoping
===================

Markdown formatting in ``scaldys-project`` is intentionally scoped to prevent
touching root-level release logs, notes, or license files:

Targeted for formatting:
------------------------

1. **``README.md``** — in the project root directory (if present).
2. **MkDocs documentation files** — all ``*.md`` files located within ``docs/``
   subdirectories that are detected as MkDocs projects (containing ``mkdocs.yml``).

Excluded from formatting:
-------------------------

* **``RELEASES.md``** — preserved as-is so release notes remain untouched.
* **Other root markdown files** — internal notes (e.g. ``ideas.md``,
  ``improvements.md``) and license files (``licenses/*.md``).
* **Sphinx documentation** — Sphinx projects in ``docs/`` typically use
  reStructuredText (``*.rst``) and are checked by ``sphinx-lint``.


Command Summary
===============

.. list-table::
   :header-rows: 1
   :widths: 35 25 15 25

   * - Command
     - Underlying action
     - Rewrites?
     - Exits non-zero on
   * - ``scaldys-project ci markdown``
     - ``uv run mdformat --check <targets>``
     - No
     - Formatting differences
   * - ``scaldys-project format markdown``
     - ``uv run mdformat <targets>``
     - Yes
     - Execution error
   * - ``scaldys-project ci all``
     - Runs all CI checks in sequence
     - No
     - Any step failure
   * - ``scaldys-project format all``
     - Runs Python and Markdown formatters
     - Yes
     - Any step failure

.. note::
   The underlying command syntax for each action is displayed in the terminal
   output at the standard ``INFO`` level in dim text.


Local Workflow
==============

The recommended developer workflow is:

1. Run ``scaldys-project ci all`` to check everything (matches GitHub Actions CI).
2. If ``ci format`` fails, run ``scaldys-project format python`` to fix Python files.
3. If ``ci markdown`` fails, run ``scaldys-project format markdown`` to fix target
   Markdown files in place.
4. Stage and commit the formatted files.
5. Re-run ``scaldys-project ci all`` to confirm all checks pass.


GitHub Actions CI
=================

In GitHub Actions (``.github/workflows/ci.yml``), Markdown formatting is verified
in the ``code_quality`` job step::

    - name: Markdown format check
      run: uv run mdformat --check README.md

Because ``mdformat`` runs with the ``--check`` flag, it will report any
unformatted files and fail the CI job without making modifications on the runner.
Running ``scaldys-project ci markdown`` locally checks all target Markdown files
and guarantees parity with the CI pipeline.
