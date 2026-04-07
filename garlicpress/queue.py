"""
Task queue builder.

Discovers source files, annotates each with git metadata (last modified date,
which imported dependencies changed more recently than the file itself), and
produces an ordered list of MapTask objects ready for the map phase.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .skeleton import INCLUDE_EXTENSIONS, SKIP_DIRS, collect_source_files, _python_imports


# ---------------------------------------------------------------------------
# Git helpers (subprocess only — no extra deps)
# ---------------------------------------------------------------------------

def _git_last_modified(repo_root: Path, file_path: Path) -> str | None:
    """Return ISO date of last commit touching this file, or None."""
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "-1", "--format=%ai", str(file_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout.strip()
        return out.split(" ")[0] if out else None  # "2026-04-01 12:00:00 +0000" -> "2026-04-01"
    except Exception:
        return None


def _git_files_changed_since(repo_root: Path, since_date: str) -> set[str]:
    """Return set of relative file paths changed after since_date."""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since_date}", "--name-only", "--format="],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except Exception:
        return set()


def _git_is_repo(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# MapTask
# ---------------------------------------------------------------------------

@dataclass
class MapTask:
    file_path: Path             # absolute
    repo_root: Path             # absolute
    relative_path: str          # relative to repo_root, forward slashes
    last_modified: str | None   # ISO date or None
    dependencies_changed_since: list[dict] = field(default_factory=list)
    # set by the runner after skeleton is built
    skeleton_path: Path | None = None
    output_path: Path | None = None

    @property
    def file_id(self) -> str:
        """Short identifier safe for use in finding_ids."""
        return self.relative_path.replace("/", "_").replace(".", "_")


# ---------------------------------------------------------------------------
# Queue builder
# ---------------------------------------------------------------------------

def build_queue(
    repo_root: Path,
    findings_root: Path,
    changed_only: bool = False,
    base_ref: str = "HEAD~1",
) -> list[MapTask]:
    """
    Discover source files and build a MapTask list.

    Args:
        repo_root:      Root of the repository to review.
        findings_root:  Where findings JSON will be written.
        changed_only:   If True, only queue files changed since base_ref.
        base_ref:       Git ref for changed_only diff base (default: HEAD~1).
    """
    is_git = _git_is_repo(repo_root)
    source_files = collect_source_files(repo_root)

    # If changed_only, filter to files in the git diff
    if changed_only and is_git:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref, "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=15,
            )
            changed = {line.strip() for line in result.stdout.splitlines() if line.strip()}
            source_files = [f for f in source_files
                            if str(f.relative_to(repo_root)) in changed]
        except Exception:
            pass  # fall back to full scan

    tasks: list[MapTask] = []
    for file_path in source_files:
        rel = str(file_path.relative_to(repo_root))
        last_mod = _git_last_modified(repo_root, file_path) if is_git else None

        # Check if any dependency was modified more recently than this file
        deps_changed: list[dict] = []
        if is_git and last_mod and file_path.suffix == ".py":
            changed_since = _git_files_changed_since(repo_root, last_mod)
            imports = _python_imports(file_path)
            for imp in imports:
                # Convert dotted module to relative path
                candidate = imp.replace(".", "/") + ".py"
                if candidate in changed_since:
                    dep_mod = _git_last_modified(repo_root, repo_root / candidate)
                    deps_changed.append({"file": candidate, "changed": dep_mod or "unknown"})

        # Mirror directory structure in findings output
        out_path = findings_root / (rel + ".json")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        tasks.append(MapTask(
            file_path=file_path,
            repo_root=repo_root,
            relative_path=rel,
            last_modified=last_mod,
            dependencies_changed_since=deps_changed,
            output_path=out_path,
        ))

    return tasks
