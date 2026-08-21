.. _publishing:

***********
Publishing
***********

This guide covers everything needed to publish ``scaldys-project`` to PyPI
using GitHub Actions with OIDC Trusted Publishing and deploy project documentation
to GitHub Pages — no API tokens or secrets to manage.

.. contents:: On this page
   :local:
   :depth: 2


Overview
========

Releases are triggered by pushing a version tag (e.g. ``v1.0.0``) to GitHub.
The ``release.yml`` workflow then builds the distributions with ``uv build``
and publishes them to PyPI via ``uv publish --trusted-publishing always``.
In parallel, the ``docs.yml`` workflow builds the Sphinx manual and deploys
the updated documentation site to GitHub Pages (``https://scaldys.github.io/scaldys-project/``).

CI (``ci.yml``) runs on every push and pull request: it lints, type-checks,
tests across Ubuntu / macOS / Windows, and verifies the build.  A release
should only be triggered once CI is green.


Why automated publishing?
==========================

``scaldys-project`` is a pure-Python, open-source build tool.  There are no
compiled extensions and no source-code protection concerns: the package
is distributed intentionally as a source-transparent wheel
(``py3-none-any``).

This makes fully automated CI publishing the right choice:

- ``uv build`` on a Linux runner produces the correct and complete artifact.
- OIDC Trusted Publishing eliminates the need to store any API token as a CI
  secret: PyPI verifies the identity of the GitHub Actions workflow directly.
- Every release goes through the same reproducible pipeline, independent of
  any developer's local machine state.

This design is intentionally different from projects derived from the
``scaldys-template`` template, which use Cython-compiled extensions.  Those
projects build their binary wheels locally (``scaldys-project build all``)
and publish manually (``scaldys-project publish``) to avoid uploading a
pure-Python source distribution that would expose protected implementation
code.  ``scaldys-project`` itself has no such constraint.


Prerequisites
=============

- A `PyPI account <https://pypi.org/account/register/>`_ with 2FA enabled
  (now required by PyPI for publishing)
- The GitHub repository must exist and have GitHub Actions enabled


Step 1 — PyPI Trusted Publishing
=================================

Trusted Publishing lets PyPI verify the identity of a GitHub Actions workflow
using OIDC tokens.  No API token or secret is stored in the repository.

1. Log in to `pypi.org <https://pypi.org>`_ and go to **Your account →
   Publishing** (or visit
   ``https://pypi.org/manage/account/publishing/`` directly).
2. Under **Add a new pending publisher**, fill in:

   ==================== ========================
   Field                Value
   ==================== ========================
   PyPI project name    ``scaldys-project``
   Owner                ``scaldys``
   Repository name      ``scaldys-project``
   Workflow name        ``release.yml``
   Environment name     ``release``
   ==================== ========================

3. Click **Add**.  PyPI will accept tokens from that exact workflow/environment
   combination and no other source.

.. note::
   Use ``testpypi`` (``test.pypi.org``) to do a dry run first.  Set up a
   separate pending publisher on Test PyPI with the same fields, and
   temporarily point the workflow at ``--index testpypi``.  See
   :ref:`testpypi_dry_run` below.


Step 2 — GitHub Environment
============================

The workflow declares ``environment: release``, which must exist in the
repository settings before the workflow can publish.

1. In the GitHub repository, go to **Settings → Environments → New
   environment**.
2. Name it ``release``.
3. Optionally add a **required reviewer** (deployment protection rule) so that
   a human must approve each publish job before it runs.
4. Save.

The ``id-token: write`` permission in the workflow is what allows GitHub to
mint the OIDC token that PyPI verifies.


Step 3 — GitHub Pages Configuration
====================================

GitHub Pages hosts the public Sphinx documentation.

1. In the GitHub repository, go to **Settings → Pages**.
2. Under **Build and deployment → Source**, select **GitHub Actions**.
3. Save.

The ``docs.yml`` workflow automatically deploys the built documentation to
GitHub Pages (``https://scaldys.github.io/scaldys-project/``) on release tags
using native GitHub Pages deployment actions.


Step 4 — Workflow Files
========================

The workflow files are located in the repository under ``.github/workflows/``.

ci.yml
------

Runs on every push and pull request::

    .github/workflows/ci.yml

Jobs:

- **code_quality** — ``ruff check``, ``ruff format --diff``, ``mdformat``,
  ``pyright``, ``sphinx-lint``
- **test** — ``pytest --cov`` on Ubuntu, macOS, and Windows
- **build** — ``uv build`` (verifies the package can be built cleanly)

release.yml
-----------

Runs when a ``v*`` tag is pushed::

    .github/workflows/release.yml

.. code-block:: yaml

    on:
      push:
        tags:
          - v*

    jobs:
      pypi:
        name: Publish to PyPI
        runs-on: ubuntu-latest
        environment:
          name: release
        permissions:
          id-token: write
        steps:
          - uses: actions/checkout@v4
          - uses: astral-sh/setup-uv@v6
          - name: Build the project
            run: uv build --index-strategy unsafe-best-match
          - name: Publish
            run: uv publish --trusted-publishing always

docs.yml
--------

Runs when a ``v*`` tag is pushed (or triggered manually via ``workflow_dispatch``)::

    .github/workflows/docs.yml

.. code-block:: yaml

    on:
      push:
        tags:
          - 'v*'
      workflow_dispatch:

    permissions:
      contents: read
      pages: write
      id-token: write

    concurrency:
      group: 'pages'
      cancel-in-progress: false

    jobs:
      deploy-docs:
        environment:
          name: github-pages
          url: ${{ steps.deployment.outputs.page_url }}
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: astral-sh/setup-uv@v6
          - name: Install documentation dependencies
            run: uv sync --only-group dev
          - name: Build Sphinx HTML documentation
            run: uv run sphinx-build -b html docs/manual/source build/manual/html
          - uses: actions/configure-pages@v5
          - uses: actions/upload-pages-artifact@v3
            with:
              path: build/manual/html
          - name: Deploy to GitHub Pages
            id: deployment
            uses: actions/deploy-pages@v4


Step 5 — Version Bump
======================

Version is declared once in ``pyproject.toml``::

    [project]
    version = "1.0.0"

It is read at runtime via ``importlib.metadata`` in
``src/scaldys_project/__about__.py``.

Before tagging a release:

1. Edit ``pyproject.toml`` and bump ``version``.
2. Update ``CHANGELOG`` with the release notes.
3. Commit both changes::

       git commit -am "Release v1.0.0"


Step 6 — Trigger a Release
============================

Push a version tag to kick off both the ``release.yml`` and ``docs.yml`` workflows::

    git tag v1.0.0
    git push origin v1.0.0

GitHub Actions will:

1. Check out the repository at the tagged commit.
2. Build and publish package distributions to PyPI via ``release.yml``.
3. Compile the Sphinx manual and deploy the updated static site to GitHub Pages
   (``https://scaldys.github.io/scaldys-project/``) via ``docs.yml``.

The package will appear on ``https://pypi.org/project/scaldys-project/``
and the updated documentation will be live on GitHub Pages within a minute or two.


.. _testpypi_dry_run:

TestPyPI Dry Run
================

Before the first real release it is a good idea to verify the full pipeline
against `Test PyPI <https://test.pypi.org>`_.

1. Create an account on ``test.pypi.org`` and add a pending publisher there
   with the same fields as in :ref:`Step 1 <publishing>` but pointing at
   ``test.pypi.org``.
2. Temporarily change the publish step in ``release.yml``::

       run: uv publish --index testpypi --trusted-publishing always

3. Push a pre-release tag::

       git tag v1.0.0rc1
       git push origin v1.0.0rc1

4. Confirm the package appears on ``https://test.pypi.org/project/scaldys-project/``.
5. Revert the workflow change before the real release.
