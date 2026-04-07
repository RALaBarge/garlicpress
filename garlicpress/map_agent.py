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

import anthropic
from pydantic import ValidationError

from .config import Config
from .queue import MapTask
from .schema import FileFindingsReport
from .skeleton import build_neighborhood, collect_source_files

logger = logging.getLogger("garlicpress.map")


async def run_map_agent(
    task: MapTask,
    client: anthropic.AsyncAnthropic,
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

    user_content = (
        f"## File to review: {task.relative_path}\n\n"
        f"```\n{file_content}\n```\n\n"
        f"{skeleton_text}\n\n"
        f"{neighborhood}\n"
        f"{temporal}"
    )

    for attempt in range(config.max_retries + 1):
        try:
            response = await client.messages.create(
                model=config.map_model,
                max_tokens=config.map_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()

            # Strip accidental markdown fences
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(raw)
            # Ensure file field matches actual file
            data["file"] = task.relative_path
            data["stable_since"] = task.last_modified
            data["dependencies_changed_since"] = [
                {"file": d["file"], "changed": d["changed"]}
                for d in task.dependencies_changed_since
            ]

            report = FileFindingsReport.model_validate(data)
            _write_findings(task, report)
            logger.info("✓ %s — %d findings", task.relative_path, len(report.findings))
            return report

        except json.JSONDecodeError as e:
            logger.warning("JSON parse error on %s (attempt %d): %s", task.relative_path, attempt + 1, e)
            if attempt < config.max_retries:
                # Feed parse error back for self-correction
                user_content += (
                    f"\n\n[CORRECTION REQUEST] Your previous response was not valid JSON. "
                    f"Error: {e}. Output ONLY the JSON object, no other text."
                )
                continue
            logger.error("Giving up on %s after %d attempts", task.relative_path, config.max_retries + 1)
            return None

        except ValidationError as e:
            logger.warning("Schema validation error on %s (attempt %d): %s", task.relative_path, attempt + 1, e)
            if attempt < config.max_retries:
                user_content += (
                    f"\n\n[CORRECTION REQUEST] Your JSON did not match the required schema. "
                    f"Errors: {e}. Fix and re-emit the complete JSON object."
                )
                continue
            return None

        except anthropic.APIError as e:
            logger.error("API error on %s: %s", task.relative_path, e)
            return None

    return None


def _write_findings(task: MapTask, report: FileFindingsReport) -> None:
    if task.output_path is None:
        return
    task.output_path.parent.mkdir(parents=True, exist_ok=True)
    task.output_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
