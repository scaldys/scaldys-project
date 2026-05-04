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

### Setting up the development environment

Clone the repository and create the virtual environment with uv:

```bash
git clone https://github.com/scaldys/scaldys-builder.git
cd scaldys-builder
uv sync --group dev
```

This installs the package in editable mode along with all development
dependencies (pytest, ruff, pyright, Sphinx, etc.).

### Running the tests

```bash
uv run pytest
```

With coverage:

```bash
uv run pytest --cov=scaldys_builder --cov-report=term-missing
```

### Linting and type checking

```bash
uv run ruff check src tests
uv run ruff format src tests
uv run pyright
```

### Building the documentation

The documentation source lives in `docs/manual/`. Build it locally with:

```bash
uv run sphinx-build -b html docs/manual/source docs/manual/build/html
```

Or use the convenience wrapper:

```bash
cd docs/manual && make html
```

### Versioning

Version is declared once in `pyproject.toml` under `[project] version`
and read at runtime via `importlib.metadata` in
`src/scaldys_builder/__about__.py`.

Update `pyproject.toml` before tagging a release.

### Building the package

Build a source distribution and wheel:

```bash
uv build
```

Outputs are written to `dist/`.

### Publishing to PyPI

Publish using uv (requires a PyPI API token configured in your environment
or `uv` settings):

```bash
uv publish
```

To publish to TestPyPI first, uncomment the `[[tool.uv.index]]` block in
`pyproject.toml` and run:

```bash
uv publish --index testpypi
```

### Consuming a local development version in another project

While iterating on the library, point a consuming project directly at the
local source tree without publishing:

```bash
# From inside the consuming project
uv add --dev "scaldys-builder @ path/to/scaldys-builder"
```

Or install in editable mode so changes are reflected immediately without
reinstalling:

```bash
uv add --dev --editable "path/to/scaldys-builder"
```

### Reporting issues

Please report bugs and feature requests on the GitHub issue tracker:

https://github.com/scaldys/scaldys-builder/issues
