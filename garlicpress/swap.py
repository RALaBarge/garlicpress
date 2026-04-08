"""
Bidirectional swap — Agent B (macro-to-micro).

Agent B never reads source code. It reads:
  - Spec files (CLAUDE.md, EVAL_SPEC.md, .allium files, etc.)
  - The reduced directory summaries from the map phase

It checks spec expectations against map-phase ground truth, producing:
  - confirmed: spec claims supported by findings
  - contradictions: spec claims violated by findings
  - ambiguous: spec claims the findings don't cover — routed to human
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from .client import LLMClient
from .config import Config
from .reduce import SUMMARY_FILENAME
from .schema import DirectorySummary, SwapReport

logger = logging.getLogger("garlicpress.swap")


def _load_summaries(findings_root: Path) -> list[DirectorySummary]:
    summaries = []
    for p in sorted(findings_root.rglob(SUMMARY_FILENAME)):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            summaries.append(DirectorySummary.model_validate(data))
        except Exception as e:
            logger.warning("Could not load summary %s: %s", p, e)
    return summaries


def _load_spec_files(spec_paths: list[Path]) -> list[tuple[str, str]]:
    """Return list of (filename, content) for all readable spec files."""
    specs = []
    for p in spec_paths:
        if p.exists():
            try:
                specs.append((p.name, p.read_text(encoding="utf-8", errors="replace")))
            except OSError as e:
                logger.warning("Cannot read spec %s: %s", p, e)
        else:
            logger.warning("Spec file not found: %s", p)
    return specs


def _build_swap_input(
    summaries: list[DirectorySummary],
    specs: list[tuple[str, str]],
) -> str:
    parts = ["# Agent B — Bidirectional Swap Input\n"]

    parts.append("## Spec Files\n")
    for name, content in specs:
        parts.append(f"### {name}\n```\n{content}\n```\n")

    parts.append("## Map Phase Findings (Ground Truth)\n")
    for s in summaries:
        parts.append(f"### Directory: {s.directory}")
        parts.append(f"Files reviewed: {s.files_reviewed}")
        parts.append(f"Summary: {s.summary}")
        if s.contradictions:
            parts.append("Internal contradictions already found:")
            for c in s.contradictions:
                parts.append(
                    f"  [{c.severity.value.upper()}] {c.file_a} assumed '{c.assumption}' "
                    f"but {c.file_b} does: '{c.actual_behavior}'"
                )
        if s.escalated_flags:
            parts.append("Escalated cross-file flags:")
            for flag in s.escalated_flags:
                parts.append(f"  - {flag}")
        parts.append("")

    return "\n".join(parts)


async def run_swap(
    findings_root: Path,
    spec_files: list[Path],
    client: LLMClient,
    config: Config,
) -> SwapReport | None:
    """Run Agent B against the reduced findings and spec files."""
    summaries = _load_summaries(findings_root)
    if not summaries:
        logger.warning("No summaries found in %s — run reduce phase first", findings_root)
        return None

    specs = _load_spec_files(spec_files)
    if not specs:
        logger.warning("No readable spec files provided — swap phase skipped")
        return None

    input_text = _build_swap_input(summaries, specs)
    system_prompt = config.prompt("swap")
    spec_names = [p.name for p in spec_files if p.exists()]

    for attempt in range(config.max_retries + 1):
        try:
            raw = await client.complete(
                model=config.swap_model,
                max_tokens=config.swap_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": input_text}],
            )
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(raw)
            data["spec_files_used"] = spec_names
            report = SwapReport.model_validate(data)

            out = findings_root / "_swap_report.json"
            out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            logger.info(
                "✓ swap complete — %d confirmed, %d contradictions, %d ambiguous",
                len(report.confirmed),
                len(report.contradictions),
                len(report.ambiguous),
            )
            return report

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Swap error (attempt %d): %s", attempt + 1, e)
            if attempt < config.max_retries:
                input_text += f"\n\n[CORRECTION] Output was invalid: {e}. Re-emit only the JSON object."
                continue
            logger.error("Swap phase failed after %d attempts", config.max_retries + 1)
            return None

        except Exception as e:
            logger.error("API error in swap: %s", e)
            return None

    return None
