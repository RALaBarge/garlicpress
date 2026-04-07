from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Model used for map agents (many calls, cost-sensitive)
    map_model: str = "claude-sonnet-4-6"
    # Model used for reduce and swap (fewer calls, higher stakes)
    reduce_model: str = "claude-sonnet-4-6"
    swap_model: str = "claude-sonnet-4-6"
    # Max parallel map workers
    concurrency: int = 5
    # Max tokens per map agent response
    map_max_tokens: int = 4096
    reduce_max_tokens: int = 4096
    swap_max_tokens: int = 4096
    # Retry on JSON parse failure
    max_retries: int = 2
    # Spec files fed to Agent B (paths relative to repo root or absolute)
    spec_files: list[str] = field(default_factory=list)
    # Only review files changed since this git ref
    changed_only: bool = False
    base_ref: str = "HEAD~1"
    # Prompts directory (defaults to package prompts/)
    prompts_dir: Path | None = None

    def prompt(self, name: str) -> str:
        """Load a prompt template by name (e.g. 'map', 'reduce', 'swap')."""
        if self.prompts_dir:
            path = self.prompts_dir / f"{name}.md"
        else:
            path = Path(__file__).parent / "prompts" / f"{name}.md"
        return path.read_text(encoding="utf-8")
