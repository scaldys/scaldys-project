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

The [Contributing guide](docs/manual/source/developers/contributing.rst) in the
manual covers everything else a contributor needs:

- Development workflow (linting, type checking, building docs, publishing)
- Internal architecture and the three-class composition pattern
- How to add a new Cython module to a consuming project
- How to add a new build step to `WindowsBuilder.main()`
- How to implement a new platform builder
