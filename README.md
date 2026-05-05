# scaldys-builder

`scaldys-builder` automates the complete Windows distribution pipeline for
Python projects. A single command takes your source code and produces a
polished Windows installer — handling Sphinx documentation, optional Cython
compilation, PyInstaller bundling, and Inno Setup packaging in one
end-to-end workflow.

If you are starting a new project, [scaldys-template](https://github.com/scaldys/scaldys-template)
provides a ready-to-use project scaffold with `scaldys-builder` already integrated:
packaging scripts, Sphinx documentation, CI/CD workflows, and a working `builder.toml`.

For a full guide on using and integrating `scaldys-builder` in your project,
see the [user documentation](https://github.com/scaldys/scaldys-builder).

---

## Development

This section is for contributors working on `scaldys-builder` itself.

Project repository and issue tracker: https://github.com/scaldys/scaldys-builder

### Quick start

```bash
git clone https://github.com/scaldys/scaldys-builder.git
cd scaldys-builder
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
- [Contributing](docs/manual/source/developers/contributing.rst) — linting,
  type checking, building docs, versioning, and publishing
