"""
Map agent — stateless async worker.

Each invocation:
  1. Loads a single source file + skeleton context
  2. Calls Claude with the map prompt
  3. Parses and validates the JSON response against FileFindingsReport
  4. Writes the findings to findings/<rel_path>.json
  5. Returns the FileFindingsReport

Context is fully isolated per call — no shared state between workers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from .client import LLMClient
from .config import Config
from .queue import MapTask
from .schema import FileFindingsReport
from .skeleton import build_neighborhood, collect_source_files

logger = logging.getLogger("garlicpress.map")


_VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
_VALID_TYPES = {
    "missing_error_path", "missing_auth", "interface_mismatch",
    "implicit_assumption_violated", "security", "logic_error",
    "missing_validation", "race_condition", "resource_leak", "other"
}

def _clean_findings(data: dict) -> dict:
    """Normalize the LLM output before Pydantic validation."""
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        data["findings"] = []
        return data
    clean = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        # Fix pipe-concatenated enums — take the first token
        for field in ("severity", "type"):
            val = f.get(field, "")
            if isinstance(val, str) and "|" in val:
                f[field] = val.split("|")[0].strip()
        # Coerce unknown severity to info
        if f.get("severity") not in _VALID_SEVERITIES:
            f["severity"] = "info"
        # Coerce unknown type to other
        if f.get("type") not in _VALID_TYPES:
            f["type"] = "other"
        # Ensure string fields are strings
        for field in ("finding_id", "location", "description", "evidence"):
            if not isinstance(f.get(field), str):
                f[field] = str(f.get(field) or "")
        clean.append(f)
    data["findings"] = clean

    # Fix list fields that the model sometimes outputs as strings
    for list_field in ("interfaces_exported", "interfaces_consumed", "explicit_requirements", "cross_file_flags"):
        val = data.get(list_field)
        if isinstance(val, str):
            data[list_field] = [val] if val else []
        elif not isinstance(val, list):
            data[list_field] = []

    return data


def _repair_json_escapes(text: str) -> str:
    """Replace invalid JSON escape sequences and control characters."""
    import re
    # Remove literal control characters inside JSON strings (unescaped \n, \t etc.)
    # We process char-by-char inside string literals
    result = []
    in_str = False
    escape = False
    for ch in text:
        if escape:
            # Valid JSON escapes: " \ / b f n r t u
            if ch not in ('"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'):
                result.append(ch)  # strip the backslash, keep char
            else:
                result.append('\\')
                result.append(ch)
            escape = False
            continue
        if ch == '\\' and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            result.append(ch)
            continue
        if in_str and ord(ch) < 0x20:
            # Escape control characters properly
            ctrl_map = {'\n': '\\n', '\r': '\\r', '\t': '\\t', '\b': '\\b', '\f': '\\f'}
            result.append(ctrl_map.get(ch, ''))
            continue
        result.append(ch)
    return ''.join(result)


def _extract_json_object(text: str) -> str:
    """
    Extract the first complete top-level JSON object from text that may contain
    prose or chain-of-thought reasoning before/after the JSON.
    Falls through to the original text if nothing is found (let json.loads raise).
    """
    # Fast path: already a clean JSON object
    stripped = text.strip()
    if stripped.startswith("{"):
        return stripped
    # Scan for the first '{' and try to find its matching '}'
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text


def _normalize_data(data: dict, task: "MapTask") -> dict:
    """Coerce the raw LLM dict into something FileFindingsReport will accept."""
    data["file"] = task.relative_path
    data["stable_since"] = task.last_modified
    data["dependencies_changed_since"] = [
        {"file": d["file"], "changed": d["changed"]}
        for d in task.dependencies_changed_since
    ]
    if not isinstance(data.get("summary"), str) or not data.get("summary"):
        data["summary"] = "(no summary)"
    data = _clean_findings(data)
    return data


def _make_stub(task: "MapTask", raw: str) -> "FileFindingsReport":
    """Minimal valid report for files where the model never produced parseable JSON."""
    from .schema import FileFindingsReport
    note = "(parse failed — raw response too malformed to extract findings)"
    if raw:
        # Try to rescue any text that looks like a finding description
        note = raw[:500].replace("\n", " ").strip() or note
    return FileFindingsReport(
        file=task.relative_path,
        summary=note,
        findings=[],
        stable_since=task.last_modified,
    )


async def run_map_agent(
    task: MapTask,
    client: LLMClient,
    config: Config,
    skeleton_text: str,
) -> FileFindingsReport | None:
    """
    Run a single stateless map agent turn for one file.
    Returns the validated FileFindingsReport, or None on unrecoverable failure.
    """
    try:
        file_content = task.file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.error("Cannot read %s: %s", task.relative_path, e)
        return None

    # Build per-file neighborhood (imported signatures only)
    source_files = collect_source_files(task.repo_root)
    neighborhood = build_neighborhood(task.file_path, task.repo_root, source_files)

    # Temporal annotation block
    temporal = ""
    if task.last_modified:
        temporal = f"\n## Temporal Metadata\nFile last modified: {task.last_modified}\n"
        if task.dependencies_changed_since:
            temporal += "Dependencies changed more recently than this file:\n"
            for dep in task.dependencies_changed_since:
                temporal += f"  - {dep['file']} (changed {dep['changed']})\n"
            temporal += "Flag any assumptions about these dependencies as HIGH RISK.\n"

    system_prompt = config.prompt("map")

    # Cap skeleton and file content so the combined prompt fits in context
    MAX_SKELETON   = 12_000   # ~3k tokens
    MAX_FILE       = 12_000   # ~3k tokens — large files get truncated
    skel = skeleton_text if len(skeleton_text) <= MAX_SKELETON else (
        skeleton_text[:MAX_SKELETON] + f"\n… [skeleton truncated at {MAX_SKELETON} chars]"
    )
    if len(file_content) > MAX_FILE:
        file_content = file_content[:MAX_FILE] + f"\n… [file truncated at {MAX_FILE} chars — review first {MAX_FILE} chars only]"

    user_content = (
        f"## File to review: {task.relative_path}\n\n"
        f"```\n{file_content}\n```\n\n"
        f"{skel}\n\n"
        f"{neighborhood}\n"
        f"{temporal}"
    )

    last_raw = ""
    for attempt in range(config.max_retries + 1):
        try:
            raw = await client.complete(
                model=config.map_model,
                max_tokens=config.map_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            last_raw = raw

            # Strip markdown fences
            stripped = raw.strip()
            if stripped.startswith("```"):
                lines = stripped.splitlines()
                stripped = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            # Find first balanced JSON object, repair escapes
            stripped = _extract_json_object(stripped)
            stripped = _repair_json_escapes(stripped)

            data = json.loads(stripped)
            data = _normalize_data(data, task)
            report = FileFindingsReport.model_validate(data)
            _write_findings(task, report)
            logger.info("✓ %s — %d findings", task.relative_path, len(report.findings))
            return report

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("%s on %s (attempt %d): %s",
                           type(e).__name__, task.relative_path, attempt + 1, e)
            if attempt < config.max_retries:
                user_content += (
                    f"\n\n[RETRY {attempt+1}] Your response was invalid: {e}. "
                    f"Output ONLY a JSON object matching the schema. No markdown, no prose."
                )
                continue
            # All retries exhausted — write a stub so the file isn't silently dropped
            report = _make_stub(task, last_raw)
            _write_findings(task, report)
            logger.warning("✗ %s — saved stub after %d failed attempts", task.relative_path, config.max_retries + 1)
            return report

        except Exception as e:
            logger.error("API error on %s: %s", task.relative_path, e)
            # Still write a stub so downstream reduce has something
            report = _make_stub(task, "")
            _write_findings(task, report)
            return report

    return None


def _write_findings(task: MapTask, report: FileFindingsReport) -> None:
    if task.output_path is None:
        return
    task.output_path.parent.mkdir(parents=True, exist_ok=True)
    task.output_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
