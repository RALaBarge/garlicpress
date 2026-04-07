"""Skeleton generator tests — no API calls required."""

import textwrap
from pathlib import Path
import pytest
from garlicpress.skeleton import _python_signatures, _python_imports, build_skeleton, collect_source_files


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_python_signatures_function(tmp_path):
    p = _write(tmp_path, "foo.py", """\
        def hello(name: str) -> str:
            return f"hi {name}"
        """)
    sigs = _python_signatures(p)
    assert any("hello" in s for s in sigs)


def test_python_signatures_class_and_method(tmp_path):
    p = _write(tmp_path, "bar.py", """\
        class MyClass(Base):
            def my_method(self, x: int) -> None:
                pass
        """)
    sigs = _python_signatures(p)
    assert any("MyClass" in s for s in sigs)
    assert any("my_method" in s for s in sigs)


def test_python_imports(tmp_path):
    p = _write(tmp_path, "baz.py", """\
        from os.path import join
        import sys
        from pathlib import Path
        """)
    imports = _python_imports(p)
    assert "sys" in imports
    assert any("join" in i for i in imports)


def test_collect_source_files(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    (tmp_path / "b.ts").write_text("const x = 1;")
    (tmp_path / "skip.txt").write_text("nope")
    skip_dir = tmp_path / "__pycache__"
    skip_dir.mkdir()
    (skip_dir / "c.py").write_text("# cached")

    files = collect_source_files(tmp_path)
    names = {f.name for f in files}
    assert "a.py" in names
    assert "b.ts" in names
    assert "skip.txt" not in names
    assert "c.py" not in names


def test_build_skeleton(tmp_path):
    _write(tmp_path, "mod.py", """\
        def greet(name: str) -> str:
            return name
        """)
    files = collect_source_files(tmp_path)
    skeleton = build_skeleton(tmp_path, files)
    assert "## API Surface" in skeleton
    assert "greet" in skeleton
    assert "## File Tree" in skeleton
