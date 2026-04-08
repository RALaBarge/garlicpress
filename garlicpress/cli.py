"""
garlicpress CLI

  garlicpress run <repo_path>          — full run: map + reduce + swap
  garlicpress map <repo_path>          — map phase only
  garlicpress reduce <findings_dir>    — reduce phase only
  garlicpress swap <findings_dir>      — swap phase only
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .client import LLMClient
from .config import Config
from .map_agent import run_map_agent
from .queue import build_queue
from .reduce import reduce_tree
from .schema import FinalReport, Severity
from .skeleton import build_skeleton, collect_source_files, write_skeleton
from .swap import run_swap

console = Console()
logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
logger = logging.getLogger("garlicpress")


def _get_client(api_key: str | None, base_url: str | None) -> LLMClient:
    resolved = api_key or os.environ.get("OPENAI_API_KEY") or "ollama"
    return LLMClient(api_key=resolved, base_url=base_url)


@click.group()
@click.version_option()
def cli() -> None:
    """GarlicPress — distributed stateless LLM code evaluation."""


# ---------------------------------------------------------------------------
# garlicpress run
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", "-o", default="findings", show_default=True,
              help="Directory to write findings into")
@click.option("--concurrency", "-c", default=5, show_default=True,
              help="Parallel map workers")
@click.option("--map-model", default="gemma3:4b", show_default=True)
@click.option("--reduce-model", default="gemma3:4b", show_default=True)
@click.option("--swap-model", default="gemma3:4b", show_default=True)
@click.option("--spec", "-s", "spec_files", multiple=True,
              help="Spec files for Agent B swap (CLAUDE.md, .allium, etc.)")
@click.option("--skip-swap", is_flag=True, help="Skip the bidirectional swap phase")
@click.option("--changed-only", is_flag=True,
              help="Only review files changed since --base-ref")
@click.option("--base-ref", default="HEAD~1", show_default=True,
              help="Git ref for --changed-only diff base")
@click.option("--base-url", default=None,
              help="Backend base URL (default: http://localhost:11434/v1)")
@click.option("--api-key", default=None, help="API key override (reads OPENAI_API_KEY if omitted)")
@click.option("--verbose", "-v", is_flag=True)
def run(
    repo_path: Path,
    output: str,
    concurrency: int,
    map_model: str,
    reduce_model: str,
    swap_model: str,
    spec_files: tuple[str, ...],
    skip_swap: bool,
    changed_only: bool,
    base_ref: str,
    base_url: str | None,
    api_key: str | None,
    verbose: bool,
) -> None:
    """Full run: map all files, reduce, then swap against spec."""
    if verbose:
        logging.getLogger("garlicpress").setLevel(logging.INFO)

    config = Config(
        map_model=map_model,
        reduce_model=reduce_model,
        swap_model=swap_model,
        concurrency=concurrency,
        spec_files=list(spec_files),
        changed_only=changed_only,
        base_ref=base_ref,
    )

    findings_root = Path(output).resolve()
    findings_root.mkdir(parents=True, exist_ok=True)

    asyncio.run(_run_all(repo_path.resolve(), findings_root, config, skip_swap, api_key, base_url))


async def _run_all(
    repo_root: Path,
    findings_root: Path,
    config: Config,
    skip_swap: bool,
    api_key: str | None = None,
    base_url: str | None = None,
) -> None:
    client = _get_client(api_key, base_url)

    # ------------------------------------------------------------------ map
    console.print(f"\n[bold cyan]garlicpress[/bold cyan] → [bold]{repo_root}[/bold]\n")

    console.print("[dim]Building skeleton...[/dim]", end=" ")
    source_files = collect_source_files(repo_root)
    skeleton_text = build_skeleton(repo_root, source_files)
    skeleton_path = findings_root / "skeleton.txt"
    skeleton_path.write_text(skeleton_text, encoding="utf-8")
    console.print(f"[green]✓[/green] {len(source_files)} files, {len(skeleton_text):,} chars")

    console.print("[dim]Building task queue...[/dim]", end=" ")
    tasks = build_queue(repo_root, findings_root, config.changed_only, config.base_ref)
    for t in tasks:
        t.skeleton_path = skeleton_path
    console.print(f"[green]✓[/green] {len(tasks)} tasks")

    map_start = time.monotonic()
    semaphore = asyncio.Semaphore(config.concurrency)
    results = []

    async def _bounded(task):
        async with semaphore:
            return await run_map_agent(task, client, config, skeleton_text)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        job = progress.add_task("[cyan]Map phase", total=len(tasks))
        coros = [_bounded(t) for t in tasks]
        for coro in asyncio.as_completed(coros):
            result = await coro
            results.append(result)
            progress.advance(job)

    map_duration = time.monotonic() - map_start
    successful = sum(1 for r in results if r is not None)
    console.print(f"\n[green]Map complete[/green] — {successful}/{len(tasks)} files in {map_duration:.1f}s\n")

    # --------------------------------------------------------------- reduce
    reduce_start = time.monotonic()
    console.print("[dim]Reducing...[/dim]")
    summaries = await reduce_tree(findings_root, client, config)
    reduce_duration = time.monotonic() - reduce_start
    total_contradictions = sum(len(s.contradictions) for s in summaries)
    console.print(f"[green]Reduce complete[/green] — {len(summaries)} directories, "
                  f"{total_contradictions} contradictions in {reduce_duration:.1f}s\n")

    # ----------------------------------------------------------------- swap
    swap_duration = 0.0
    swap_report = None
    if not skip_swap and config.spec_files:
        swap_start = time.monotonic()
        console.print("[dim]Running swap (Agent B)...[/dim]")
        spec_paths = [Path(s) for s in config.spec_files]
        swap_report = await run_swap(findings_root, spec_paths, client, config)
        swap_duration = time.monotonic() - swap_start
        if swap_report:
            console.print(
                f"[green]Swap complete[/green] — "
                f"{len(swap_report.confirmed)} confirmed, "
                f"{len(swap_report.contradictions)} contradictions, "
                f"{len(swap_report.ambiguous)} ambiguous in {swap_duration:.1f}s\n"
            )
    elif not skip_swap:
        console.print("[yellow]Skipping swap — no --spec files provided[/yellow]\n")

    # -------------------------------------------------------------- report
    _print_summary(results, summaries, swap_report, map_duration, reduce_duration, swap_duration)


def _print_summary(results, summaries, swap_report, map_s, reduce_s, swap_s):
    all_findings = [f for r in results if r for f in r.findings]
    by_severity: dict[str, int] = {}
    for sev in Severity:
        count = sum(1 for f in all_findings if f.severity == sev)
        by_severity[sev.value] = count

    table = Table(title="Findings by Severity", show_header=True)
    table.add_column("Severity", style="bold")
    table.add_column("Count", justify="right")
    colors = {"critical": "red", "high": "yellow", "medium": "cyan", "low": "dim", "info": "dim"}
    for sev, count in by_severity.items():
        if count:
            table.add_row(f"[{colors[sev]}]{sev}[/{colors[sev]}]", str(count))
    console.print(table)

    all_contradictions = [c for s in summaries for c in s.contradictions]
    if all_contradictions:
        ctable = Table(title="Cross-File Contradictions", show_header=True)
        ctable.add_column("Severity", style="bold")
        ctable.add_column("File A")
        ctable.add_column("Assumption")
        ctable.add_column("File B")
        ctable.add_column("Actual Behavior")
        for c in sorted(all_contradictions, key=lambda x: list(Severity).index(x.severity)):
            ctable.add_row(
                c.severity.value,
                Path(c.file_a).name,
                c.assumption[:60],
                Path(c.file_b).name,
                c.actual_behavior[:60],
            )
        console.print(ctable)

    if swap_report and swap_report.contradictions:
        stable = Table(title="Spec Contradictions (Agent B)", show_header=True)
        stable.add_column("ID")
        stable.add_column("Severity")
        stable.add_column("Spec Says")
        stable.add_column("Code Does")
        for sc in swap_report.contradictions:
            stable.add_row(
                sc.finding_id,
                sc.severity.value,
                sc.spec_expectation[:60],
                sc.observed_behavior[:60],
            )
        console.print(stable)

        if swap_report.ambiguous:
            console.print(f"\n[yellow]⚠ {len(swap_report.ambiguous)} ambiguous items routed to human review[/yellow]")
            for a in swap_report.ambiguous:
                console.print(f"  [{a.finding_id}] {a.description}")

    console.print(
        f"\n[dim]Map {map_s:.1f}s · Reduce {reduce_s:.1f}s · Swap {swap_s:.1f}s[/dim]\n"
    )


# ---------------------------------------------------------------------------
# Phase-only commands
# ---------------------------------------------------------------------------

@cli.command("map")
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", "-o", default="findings", show_default=True)
@click.option("--concurrency", "-c", default=5, show_default=True)
@click.option("--model", default="gemma3:4b", show_default=True)
@click.option("--changed-only", is_flag=True)
@click.option("--base-ref", default="HEAD~1", show_default=True)
@click.option("--base-url", default=None)
@click.option("--api-key", default=None)
@click.option("--verbose", "-v", is_flag=True)
def map_cmd(repo_path, output, concurrency, model, changed_only, base_ref, base_url, api_key, verbose):
    """Run the map phase only."""
    if verbose:
        logging.getLogger("garlicpress").setLevel(logging.INFO)
    config = Config(map_model=model, concurrency=concurrency, changed_only=changed_only, base_ref=base_ref)
    findings_root = Path(output).resolve()
    findings_root.mkdir(parents=True, exist_ok=True)
    asyncio.run(_run_map_only(repo_path.resolve(), findings_root, config, api_key, base_url))


async def _run_map_only(repo_root, findings_root, config, api_key=None, base_url=None):
    client = _get_client(api_key, base_url)
    source_files = collect_source_files(repo_root)
    skeleton_text = build_skeleton(repo_root, source_files)
    tasks = build_queue(repo_root, findings_root, config.changed_only, config.base_ref)
    semaphore = asyncio.Semaphore(config.concurrency)

    async def _bounded(task):
        async with semaphore:
            return await run_map_agent(task, client, config, skeleton_text)

    results = await asyncio.gather(*[_bounded(t) for t in tasks])
    successful = sum(1 for r in results if r is not None)
    console.print(f"[green]Map complete[/green] — {successful}/{len(tasks)} files")


@cli.command("reduce")
@click.argument("findings_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--model", default="gemma3:4b", show_default=True)
@click.option("--base-url", default=None)
@click.option("--api-key", default=None)
@click.option("--verbose", "-v", is_flag=True)
def reduce_cmd(findings_dir, model, base_url, api_key, verbose):
    """Run the reduce phase on an existing findings directory."""
    if verbose:
        logging.getLogger("garlicpress").setLevel(logging.INFO)
    config = Config(reduce_model=model)
    asyncio.run(_run_reduce_only(findings_dir.resolve(), config, api_key, base_url))


async def _run_reduce_only(findings_root, config, api_key=None, base_url=None):
    client = _get_client(api_key, base_url)
    summaries = await reduce_tree(findings_root, client, config)
    contradictions = sum(len(s.contradictions) for s in summaries)
    console.print(f"[green]Reduce complete[/green] — {len(summaries)} dirs, {contradictions} contradictions")


@cli.command("swap")
@click.argument("findings_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--spec", "-s", "spec_files", multiple=True, required=True)
@click.option("--model", default="gemma3:4b", show_default=True)
@click.option("--base-url", default=None)
@click.option("--api-key", default=None)
@click.option("--verbose", "-v", is_flag=True)
def swap_cmd(findings_dir, spec_files, model, base_url, api_key, verbose):
    """Run Agent B swap against existing reduced findings."""
    if verbose:
        logging.getLogger("garlicpress").setLevel(logging.INFO)
    config = Config(swap_model=model, spec_files=list(spec_files))
    asyncio.run(_run_swap_only(findings_dir.resolve(), config, api_key, base_url))


async def _run_swap_only(findings_root, config, api_key=None, base_url=None):
    client = _get_client(api_key, base_url)
    spec_paths = [Path(s) for s in config.spec_files]
    report = await run_swap(findings_root, spec_paths, client, config)
    if report:
        console.print(
            f"[green]Swap complete[/green] — "
            f"{len(report.confirmed)} confirmed, "
            f"{len(report.contradictions)} contradictions, "
            f"{len(report.ambiguous)} ambiguous"
        )
