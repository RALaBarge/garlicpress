"""
Hierarchical tree-reduce phase.

Walks the findings directory bottom-up (leaves first). At each directory level:
  - Loads all .json findings files for files directly in that directory
  - Loads any child directory summaries (_summary.json)
  - Calls Claude to synthesize contradictions and produce a DirectorySummary
  - Writes <dir>/_summary.json

The root-level summary becomes the spine of the final report.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from .client import LLMClient
from .config import Config
from .map_agent import _extract_json_object, _repair_json_escapes
from .schema import DirectorySummary, FileFindingsReport

logger = logging.getLogger("garlicpress.reduce")

SUMMARY_FILENAME = "_summary.json"


def _load_file_findings(dir_path: Path) -> list[FileFindingsReport]:
    """Load all per-file findings JSONs directly in dir_path (not subdirs)."""
    reports = []
    for p in sorted(dir_path.glob("*.json")):
        if p.name == SUMMARY_FILENAME:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            reports.append(FileFindingsReport.model_validate(data))
        except Exception as e:
            logger.warning("Could not load findings %s: %s", p, e)
    return reports


def _load_child_summaries(dir_path: Path) -> list[DirectorySummary]:
    """Load _summary.json from immediate subdirectories."""
    summaries = []
    for child in sorted(dir_path.iterdir()):
        if not child.is_dir():
            continue
        summary_path = child / SUMMARY_FILENAME
        if summary_path.exists():
            try:
                data = json.loads(summary_path.read_text(encoding="utf-8"))
                summaries.append(DirectorySummary.model_validate(data))
            except Exception as e:
                logger.warning("Could not load summary %s: %s", summary_path, e)
    return summaries


def _build_reduce_input(
    dir_path: Path,
    findings_root: Path,
    file_reports: list[FileFindingsReport],
    child_summaries: list[DirectorySummary],
) -> str:
    rel_dir = dir_path.relative_to(findings_root)
    parts = [f"# Directory: {rel_dir}\n"]

    if file_reports:
        parts.append("## Per-File Findings\n")
        for r in file_reports:
            parts.append(f"### {r.file}")
            parts.append(f"Summary: {r.summary}")
            if r.findings:
                parts.append("Findings:")
                for f in r.findings:
                    parts.append(
                        f"  [{f.finding_id}] {f.severity.value.upper()} {f.type.value} "
                        f"@ {f.location}: {f.description}"
                    )
            if r.implicit_assumptions:
                parts.append("Implicit Assumptions:")
                for a in r.implicit_assumptions:
                    parts.append(f"  [{a.confidence}] {a.assumption} (risk: {a.risk})")
            if r.interfaces_exported:
                parts.append(f"Exports: {', '.join(r.interfaces_exported[:5])}")
            if r.cross_file_flags:
                parts.append("Cross-file flags:")
                for flag in r.cross_file_flags:
                    parts.append(f"  - {flag}")
            parts.append("")

    if child_summaries:
        parts.append("## Child Directory Summaries\n")
        for s in child_summaries:
            parts.append(f"### {s.directory}")
            parts.append(s.summary)
            if s.contradictions:
                parts.append(f"Contradictions: {len(s.contradictions)}")
            if s.escalated_flags:
                parts.append("Escalated flags:")
                for flag in s.escalated_flags:
                    parts.append(f"  - {flag}")
            parts.append("")

    return "\n".join(parts)


async def reduce_directory(
    dir_path: Path,
    findings_root: Path,
    client: LLMClient,
    config: Config,
) -> DirectorySummary | None:
    """Reduce a single directory and write its _summary.json."""
    file_reports = _load_file_findings(dir_path)
    child_summaries = _load_child_summaries(dir_path)

    if not file_reports and not child_summaries:
        return None

    rel_dir = str(dir_path.relative_to(findings_root))
    total_files = len(file_reports) + sum(s.files_reviewed for s in child_summaries)

    input_text = _build_reduce_input(dir_path, findings_root, file_reports, child_summaries)
    system_prompt = config.prompt("reduce")

    for attempt in range(config.max_retries + 1):
        try:
            raw = await client.complete(
                model=config.reduce_model,
                max_tokens=config.reduce_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": input_text}],
            )
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            raw = _extract_json_object(raw)
            raw = _repair_json_escapes(raw)

            data = json.loads(raw)
            data["directory"] = rel_dir
            data["files_reviewed"] = total_files

            # Normalize contradictions — coerce None strings to ""
            for c in data.get("contradictions", []):
                if not isinstance(c, dict):
                    continue
                for field in ("file_a", "file_b", "assumption", "actual_behavior", "description"):
                    if not isinstance(c.get(field), str):
                        c[field] = str(c.get(field) or "")
                if not isinstance(c.get("finding_ids"), list):
                    c["finding_ids"] = []

            # Normalize other list/string fields
            for field in ("escalated_flags",):
                val = data.get(field)
                if isinstance(val, str):
                    data[field] = [val] if val else []
                elif not isinstance(val, list):
                    data[field] = []

            if not isinstance(data.get("summary"), str) or not data.get("summary"):
                data["summary"] = "(no summary)"

            summary = DirectorySummary.model_validate(data)
            out = dir_path / SUMMARY_FILENAME
            out.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
            logger.info("✓ reduced %s — %d contradictions", rel_dir, len(summary.contradictions))
            return summary

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Reduce error for %s (attempt %d): %s", rel_dir, attempt + 1, e)
            if attempt < config.max_retries:
                input_text += f"\n\n[CORRECTION] Output was invalid: {e}. Re-emit only the JSON object."
                continue
            logger.error("Giving up on reduce for %s — writing stub summary", rel_dir)
            stub = DirectorySummary(
                directory=rel_dir,
                files_reviewed=total_files,
                summary="(reduce failed — parse error on all attempts)",
            )
            out = dir_path / SUMMARY_FILENAME
            out.write_text(stub.model_dump_json(indent=2), encoding="utf-8")
            return stub

        except Exception as e:
            logger.error("API error reducing %s: %s", rel_dir, e)
            return None

    return None


async def reduce_tree(
    findings_root: Path,
    client: LLMClient,
    config: Config,
) -> list[DirectorySummary]:
    """
    Walk findings_root bottom-up and reduce each directory level.
    Returns all produced DirectorySummary objects (root last).
    """
    # Collect all directories that have findings, deepest first
    dirs_with_content: list[Path] = []
    for p in sorted(findings_root.rglob("*.json")):
        if p.name == SUMMARY_FILENAME:
            continue
        if p.parent not in dirs_with_content:
            dirs_with_content.append(p.parent)

    # Sort by depth descending (leaves first)
    dirs_with_content.sort(key=lambda p: len(p.parts), reverse=True)

    # Also include the root itself
    if findings_root not in dirs_with_content:
        dirs_with_content.append(findings_root)

    summaries = []
    for dir_path in dirs_with_content:
        summary = await reduce_directory(dir_path, findings_root, client, config)
        if summary:
            summaries.append(summary)

    return summaries
