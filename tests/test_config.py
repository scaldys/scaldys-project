import tempfile
from pathlib import Path

from scaldys_builder.common.config import load_config


def test_load_config_defaults_when_no_file():
    """load_config returns all defaults when builder.toml is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(Path(tmpdir))
    assert config.cython.compiled_modules == []
    assert config.cython.source_root == "src"
    assert config.windows.script_dir == "packaging/windows"


def test_load_config_reads_compiled_modules():
    """load_config reads compiled_modules from [cython] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text(
            '[cython]\ncompiled_modules = ["myapp.core.foo", "myapp.core.bar"]\n'
        )
        config = load_config(Path(tmpdir))
    assert config.cython.compiled_modules == ["myapp.core.foo", "myapp.core.bar"]


def test_load_config_reads_source_root():
    """load_config reads source_root from [cython] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text('[cython]\nsource_root = "source"\n')
        config = load_config(Path(tmpdir))
    assert config.cython.source_root == "source"


def test_load_config_reads_windows_script_dir():
    """load_config reads script_dir from [windows] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text('[windows]\nscript_dir = "build/win"\n')
        config = load_config(Path(tmpdir))
    assert config.windows.script_dir == "build/win"


def test_load_config_partial_cython_section():
    """load_config applies defaults for keys absent from a partial [cython] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text("[cython]\ncompiled_modules = []\n")
        config = load_config(Path(tmpdir))
    assert config.cython.source_root == "src"
    assert config.windows.script_dir == "packaging/windows"


def test_load_config_empty_file():
    """load_config returns all defaults for an empty builder.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text("")
        config = load_config(Path(tmpdir))
    assert config.cython.compiled_modules == []
    assert config.cython.source_root == "src"
    assert config.windows.script_dir == "packaging/windows"


def test_load_config_defaults_docs_section():
    """load_config returns empty lists for docs when section is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(Path(tmpdir))
    assert config.docs.dist_dirs == []
    assert config.docs.apidoc_dirs == []


def test_load_config_reads_dist_dirs():
    """load_config reads dist_dirs from [docs] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text('[docs]\ndist_dirs = ["manual"]\n')
        config = load_config(Path(tmpdir))
    assert config.docs.dist_dirs == ["manual"]
    assert config.docs.apidoc_dirs == []


def test_load_config_reads_apidoc_dirs():
    """load_config reads apidoc_dirs from [docs] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text('[docs]\napidoc_dirs = ["developer_guide"]\n')
        config = load_config(Path(tmpdir))
    assert config.docs.apidoc_dirs == ["developer_guide"]
    assert config.docs.dist_dirs == []


def test_load_config_reads_full_docs_section():
    """load_config reads both dist_dirs and apidoc_dirs from [docs] section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text(
            '[docs]\ndist_dirs = ["manual"]\napidoc_dirs = ["developer_guide"]\n'
        )
        config = load_config(Path(tmpdir))
    assert config.docs.dist_dirs == ["manual"]
    assert config.docs.apidoc_dirs == ["developer_guide"]


def test_load_config_docs_defaults_when_empty_file():
    """load_config returns docs defaults for an empty builder.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "builder.toml").write_text("")
        config = load_config(Path(tmpdir))
    assert config.docs.dist_dirs == []
    assert config.docs.apidoc_dirs == []
