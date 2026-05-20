# scaldys-project

`scaldys-project` automates the complete Windows distribution pipeline for
Python projects. A single command takes your source code through Sphinx
documentation, optional Cython compilation, and — depending on the chosen
deployment mode — one of three distribution strategies:

- **wheel_only** (default) — binary wheel only, no installer (for
  pip-installable apps)
- **pyinstaller** — PyInstaller exe + Inno Setup installer
- **pyruntime** — binary wheel + Inno Setup installer with a managed Python
  runtime (for apps that coexist with Quarto/Jupyter)

If you are starting a new project, use `scaldys-project init` to scaffold one
from [scaldys-template](https://github.com/scaldys/scaldys-template) in a single
command. The interactive wizard collects your project name, author details, and
deployment mode, then downloads the template, substitutes all placeholder names,
and optionally runs `git init` and `uv sync`:

```bash
scaldys-project init
```

`scaldys-template` provides a ready-to-use scaffold with `scaldys-project`
already integrated: packaging scripts, Sphinx documentation, CI/CD workflows,
and a working `scaldys-project.toml`.

For a full guide on using and integrating `scaldys-project` in your project, see
the [user documentation](https://github.com/scaldys/scaldys-project).

---

## Development

This section is for contributors working on `scaldys-project` itself.

Project repository and issue tracker: https://github.com/scaldys/scaldys-project

### Quick start

```bash
git clone https://github.com/scaldys/scaldys-project.git
cd scaldys-project
uv sync --group dev
uv run pytest
uv run ruff check src tests && uv run pyright
```

### Further reading

The manual's Developers section covers everything else a contributor needs:

- [Architecture](docs/manual/source/developers/architecture.rst) — module
  layout, three-class composition pattern, execution flow, configuration
  loading, and why `compile_runner.py` runs as a subprocess
- [Extension Points](docs/manual/source/developers/extension_points.rst) —
  design conventions and how to add Cython modules, build steps, or a new
  platform builder
- [Contributing](docs/manual/source/developers/contributing.rst) — linting, type
  checking, building docs, versioning, and publishing
