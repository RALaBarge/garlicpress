"""
AST-based project skeleton generator.

Produces two artifacts:
  skeleton.txt   — full project API surface (file tree + all signatures)
  neighborhood   — per-file call graph: which signatures this file imports/calls

Python files are parsed with the `ast` module. Other languages get a regex
fallback that extracts function/class definition lines.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# File tree
# ---------------------------------------------------------------------------

def _build_tree_lines(root: Path, paths: list[Path]) -> list[str]:
    """Render a simple indented file tree."""
    lines = [f"{root.name}/"]
    for p in sorted(paths):
        rel = p.relative_to(root)
        parts = rel.parts
        indent = "  " * (len(parts) - 1)
        lines.append(f"{indent}├── {parts[-1]}")
    return lines


# ---------------------------------------------------------------------------
# Python signature extraction
# ---------------------------------------------------------------------------

def _python_signatures(path: Path) -> list[str]:
    """Return all top-level and class-method signatures from a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    sigs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
            sigs.append(f"class {node.name}({bases}):")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sigs.append(f"    {_fn_sig(item)}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only top-level functions (parent is Module)
            if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   for node in ast.walk(tree)
                   if node is node):
                sigs.append(_fn_sig(node))

    # deduplicate while preserving order
    seen: set[str] = set()
    out = []
    for s in sigs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _fn_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    try:
        args = ast.unparse(node.args)
    except Exception:
        args = "..."
    ret = ""
    if node.returns:
        try:
            ret = f" -> {ast.unparse(node.returns)}"
        except Exception:
            pass
    return f"{prefix} {node.name}({args}){ret}: ..."


# ---------------------------------------------------------------------------
# Python import extraction (for call graph)
# ---------------------------------------------------------------------------

def _python_imports(path: Path) -> list[str]:
    """Return module-level imported names from a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
    return imports


# ---------------------------------------------------------------------------
# Fallback regex extraction (non-Python)
# ---------------------------------------------------------------------------

_PATTERNS = {
    ".ts": re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+\w+|^(?:export\s+)?class\s+\w+", re.M),
    ".js": re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+\w+|^(?:export\s+)?class\s+\w+", re.M),
    ".go": re.compile(r"^func\s+\w+|^type\s+\w+\s+struct", re.M),
    ".rs": re.compile(r"^pub\s+(?:async\s+)?fn\s+\w+|^pub\s+struct\s+\w+", re.M),
    ".java": re.compile(r"^\s*(?:public|private|protected)\s+.*\w+\s*\(", re.M),
}

def _generic_signatures(path: Path) -> list[str]:
    pattern = _PATTERNS.get(path.suffix)
    if not pattern:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return [m.group().strip() for m in pattern.finditer(text)]
    except OSError:
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build", ".mypy_cache", ".claude", "findings", "skills"}
INCLUDE_EXTENSIONS = {".py", ".ts", ".js", ".go", ".rs", ".java"}


def collect_source_files(repo_root: Path) -> list[Path]:
    files = []
    for p in sorted(repo_root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix in INCLUDE_EXTENSIONS:
            files.append(p)
    return files


def build_skeleton(repo_root: Path, source_files: list[Path]) -> str:
    """
    Build the full project skeleton text. This is injected into every map
    agent alongside the file under review.

    Format:
        # Project Skeleton
        ## File Tree
        ...
        ## API Surface
        ### path/to/file.py
        def foo(...): ...
        class Bar: ...
    """
    lines: list[str] = [
        "# Project Skeleton",
        f"# Root: {repo_root}",
        f"# Files: {len(source_files)}",
        "",
        "## File Tree",
    ]
    lines.extend(_build_tree_lines(repo_root, source_files))
    lines.append("")
    lines.append("## API Surface")

    for path in source_files:
        rel = path.relative_to(repo_root)
        if path.suffix == ".py":
            sigs = _python_signatures(path)
        else:
            sigs = _generic_signatures(path)
        if not sigs:
            continue
        lines.append(f"\n### {rel}")
        lines.extend(sigs)

    return "\n".join(lines)


def build_neighborhood(target: Path, repo_root: Path, source_files: list[Path]) -> str:
    """
    Build the local call-graph neighborhood for a single file.

    Returns the subset of skeleton entries that `target` imports, so the map
    agent sees exactly which external signatures are relevant without loading
    the full skeleton again.
    """
    if target.suffix != ".py":
        return ""

    imported = _python_imports(target)
    if not imported:
        return ""

    # Map module paths to source files
    def _rel_to_module(p: Path) -> str:
        rel = p.relative_to(repo_root)
        return str(rel).replace("/", ".").removesuffix(".py")

    module_map: dict[str, Path] = {_rel_to_module(p): p for p in source_files}

    lines = ["## Local Call Graph Neighborhood"]
    for imp in imported:
        # Try exact match, then prefix match
        match = module_map.get(imp)
        if match is None:
            for mod, path in module_map.items():
                if imp.startswith(mod):
                    match = path
                    break
        if match is None:
            continue
        rel = match.relative_to(repo_root)
        sigs = _python_signatures(match) if match.suffix == ".py" else _generic_signatures(match)
        if sigs:
            lines.append(f"\n### {rel}  (imported by {target.relative_to(repo_root)})")
            lines.extend(sigs)

    return "\n".join(lines) if len(lines) > 1 else ""


def write_skeleton(repo_root: Path, output_path: Path) -> Path:
    """Generate skeleton.txt and write it to output_path. Returns the path."""
    files = collect_source_files(repo_root)
    text = build_skeleton(repo_root, files)
    output_path.write_text(text, encoding="utf-8")
    return output_path
