import tempfile
from pathlib import Path

from scaldys_project.common.config import load_config


def test_load_config_defaults_when_no_file():
    """load_config returns all defaults when scaldys-project.toml is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(Path(tmpdir))
    assert config.cython.compiled_modules == []
    assert config.cython.source_root == "src"
    assert config.windows.script_dir == "packaging/windows"


def test_load_config_reads_compiled_modules():
    """load_config reads compiled_modules from the [cython] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "scaldys-project.toml").write_text(
            '[cython]\ncompiled_modules = ["myapp.core.foo", "myapp.core.bar"]\n'
        )
        config = load_config(Path(tmpdir))
    assert config.cython.compiled_modules == ["myapp.core.foo", "myapp.core.bar"]


def test_load_config_reads_source_root():
    """load_config reads source_root from the [cython] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "scaldys-project.toml").write_text('[cython]\nsource_root = "source"\n')
        config = load_config(Path(tmpdir))
    assert config.cython.source_root == "source"


def test_load_config_reads_windows_script_dir():
    """load_config reads script_dir from the [windows] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "scaldys-project.toml").write_text('[windows]\nscript_dir = "build/win"\n')
        config = load_config(Path(tmpdir))
    assert config.windows.script_dir == "build/win"


def test_load_config_partial_cython_section():
    """load_config applies defaults for keys absent from a partial [cython] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "scaldys-project.toml").write_text("[cython]\ncompiled_modules = []\n")
        config = load_config(Path(tmpdir))
    assert config.cython.source_root == "src"
    assert config.windows.script_dir == "packaging/windows"


def test_load_config_empty_file():
    """load_config returns all defaults for an empty scaldys-project.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "scaldys-project.toml").write_text("")
        config = load_config(Path(tmpdir))
    assert config.cython.compiled_modules == []
    assert config.cython.source_root == "src"
    assert config.windows.script_dir == "packaging/windows"


def test_load_config_defaults_docs_section():
    """load_config returns an empty list for docs when the section is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(Path(tmpdir))
    assert config.docs.public_doc_dirs == []


def test_load_config_reads_public_doc_dirs():
    """load_config reads public_doc_dirs from the [docs] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "scaldys-project.toml").write_text('[docs]\npublic_doc_dirs = ["manual"]\n')
        config = load_config(Path(tmpdir))
    assert config.docs.public_doc_dirs == ["manual"]


def test_load_config_docs_defaults_when_empty_file():
    """load_config returns docs defaults for an empty scaldys-project.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "scaldys-project.toml").write_text("")
        config = load_config(Path(tmpdir))
    assert config.docs.public_doc_dirs == []
