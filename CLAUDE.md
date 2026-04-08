# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**garlicpress** — Distributed stateless LLM code evaluation. The tool runs structured LLM-based code review in parallel (map), synthesizes findings (reduce), then validates against project spec (swap).

## Architecture: Map → Reduce → Swap

The core pipeline has three distinct phases:

### Map Phase
- **File**: `garlicpress/map_agent.py`
- **CLI**: `garlicpress map <repo_path>`
- Stateless async workers, one per source file, run in parallel
- Each agent:
  1. Loads the source file + AST-based skeleton context
  2. Sends the file to an LLM with a structured prompt
  3. Parses JSON response into `FileFindingsReport`
  4. Writes `findings/<rel_path>.json`
- Output: Per-file findings with detected issues, exported/consumed interfaces, implicit assumptions
- **Key insight**: No shared state between workers—entirely parallelizable

### Reduce Phase
- **File**: `garlicpress/reduce.py`
- **CLI**: `garlicpress reduce <findings_dir>`
- Walks the findings directory tree bottom-up (leaves to root)
- At each directory level:
  1. Loads all per-file findings in that directory
  2. Loads child directory summaries
  3. Calls LLM to synthesize contradictions and produce `DirectorySummary`
  4. Writes `<dir>/_summary.json`
- Detects cross-file contradictions: "File A assumed X, but File B actually does Y"
- **Key insight**: Hierarchical tree-fold detects contradictions without re-reading source code

### Swap Phase (Agent B)
- **File**: `garlicpress/swap.py`
- **CLI**: `garlicpress swap <findings_dir> --spec CLAUDE.md`
- Agent B validates findings against the spec (CLAUDE.md, .allium files, etc.)
- **Critical design**: Agent B reads ONLY the spec and map findings, never the source code
- Produces `SwapReport`: confirmed behaviors, contradictions, ambiguous items routed to humans
- **Why it matters**: Ensures spec/code alignment without re-reading files

## Key Modules

| Module | Purpose |
|--------|---------|
| `cli.py` | Entry point; orchestrates the full pipeline and phase-only commands |
| `schema.py` | Pydantic models: `FileFindingsReport`, `DirectorySummary`, `SwapReport`, `Finding`, etc. |
| `map_agent.py` | Stateless map worker: loads file, calls LLM, parses JSON, writes findings |
| `reduce.py` | Hierarchical reduce: walks findings tree, detects cross-file contradictions |
| `swap.py` | Agent B: validates findings against spec without reading source |
| `client.py` | LLM client abstraction—supports Ollama native API or OpenAI-compatible backends |
| `skeleton.py` | AST-based project skeleton generator; produces file tree + function signatures |
| `queue.py` | Task queue builder—walks repo, creates one `MapTask` per source file |
| `config.py` | Configuration dataclass; loads prompts from `garlicpress/prompts/` |

## Finding Types and Severity

**Severity**: `critical`, `high`, `medium`, `low`, `info`

**Finding Types**:
- `missing_error_path` — uncaught exception or error case
- `missing_auth` — missing authorization check
- `interface_mismatch` — caller/callee contract violation
- `implicit_assumption_violated` — assumption in one file breaks in another
- `security` — security vulnerability
- `logic_error` — incorrect implementation
- `missing_validation` — missing input validation
- `race_condition` — concurrent access issue
- `resource_leak` — resource not freed
- `other` — anything else

## Development Commands

```bash
# Install in editable mode
pip install -e .

# Run full pipeline against a test repo
garlicpress run /path/to/repo --spec CLAUDE.md --map-model llama3.2:3b

# Run individual phases
garlicpress map /path/to/repo --output findings/
garlicpress reduce findings/
garlicpress swap findings/ --spec CLAUDE.md

# Run tests
pytest tests/

# Run a specific test
pytest tests/test_schema.py::test_<name> -v

# Install test dependencies (if needed)
pip install pytest pytest-asyncio
```

## Testing

Tests are in `tests/`:
- `test_schema.py` — Pydantic schema validation; verifies JSON parsing resilience
- `test_skeleton.py` — Skeleton generation; verifies AST parsing and file tree building

Run with `pytest tests/ -v`.

## Key Concepts

### Skeleton
Generated at the start of map phase; contains:
- File tree of all source files in the repo
- Function/class signatures (parsed with `ast` for Python, regex fallback for others)
- Up to 10,240 tokens (capped for consumer GPU VRAM)

Each map agent receives the skeleton as context to understand the broader codebase.

### Implicit Assumptions
Each file may declare assumptions it makes about other parts of the system. These are fed into the reduce phase to detect contradictions. Examples:
- "The `User` class always has an `id` field"
- "Database transactions are always committed before returning"
- "The logger is never None"

### Cross-File Contradictions
When reduce detects that File A assumes something but File B violates it, that's a contradiction:
```
File A assumes: "request.user is always populated by auth middleware"
File B violates: "Calls request.user without checking for None"
```

### JSON Repair
Both map and reduce agents may emit slightly malformed JSON (unescaped newlines, pipe-concatenated enums, etc.). The code includes:
- `_repair_json_escapes()` — cleans literal control characters
- `_clean_findings()` — normalizes severity/type enums, coerces unknown values
- `_extract_json_object()` — extracts JSON block from LLM response that may include preamble/explanation

## Configuration

### Models
Default model is `gemma3:4b` (Ollama). Can be overridden:
```bash
garlicpress run . --map-model gpt-4o --reduce-model gpt-4o --swap-model gpt-4o
```

Recommendations:
- **Fast local**: `llama3.2:3b` (~12s/file)
- **Quality local**: `qwen3:8b`, `gemma3:12b`
- **Best results**: `claude-sonnet-4-6`, `gpt-4o`

### Prompts
Prompts are stored in `garlicpress/prompts/`:
- `map.md` — instructions for map agents
- `reduce.md` — instructions for reduce agents
- `swap.md` — instructions for Agent B

Load with `config.prompt(name)`. Can be overridden with `Config(prompts_dir=...)`.

### Backends
- **Ollama** (default): `http://localhost:11434/api/chat` — native endpoint, sends `think: false`
- **OpenAI-compatible**: any URL + API key (OpenAI, Anthropic, etc.)

Detection logic in `client.py:_is_ollama()`.

## Output Structure

```
findings/
  skeleton.txt              # Generated API surface
  beigebox/
    proxy.py.json           # FileFindingsReport per file
    main.py.json
    backends/
      router.py.json
      _summary.json         # DirectorySummary per directory
    _summary.json
  _summary.json             # Root summary
  _swap_report.json         # SwapReport from Agent B
```

## Important Design Notes

1. **Statelessness**: Map agents have zero shared state—purely functional. This is why they're so parallelizable.

2. **Two-pass spec validation**: Agent B doesn't re-read source code; it validates the map phase output against spec. This prevents spec-drift and keeps the swap phase fast.

3. **Graceful degradation**: If an agent fails to parse JSON, the code retries (up to `max_retries`) or skips the file entirely. Contradictions are still synthesized from available findings.

4. **Token budgets**: Context is capped at 10,240 tokens for map agents (to fit Ollama on consumer GPUs). The skeleton is truncated if necessary.

5. **Language support**: Python files use the `ast` module for perfect signature extraction. Other languages use regex fallback. This is why skeleton extraction is robust but not grammar-perfect for non-Python.

## Debugging

Enable verbose logging:
```bash
garlicpress run . --spec CLAUDE.md -v
```

This sets the garlicpress logger to INFO level, showing:
- LLM requests/responses
- JSON parsing attempts and repairs
- File loading errors
- Reduce phase synthesis

## CI Integration

Typical CI usage:
```yaml
- name: garlicpress review
  run: |
    pip install garlicpress
    garlicpress run . --changed-only --skip-swap \
      --map-model llama3.2:3b \
      --output findings/
```

Use `--changed-only` to only review files changed since `--base-ref` (default: `HEAD~1`).
