# garlicpress

Distributed stateless LLM code evaluation. Point it at a repo, get back structured findings.

**Map → Reduce → Swap**

- **Map** — stateless agents review one file each in parallel, emitting structured JSON findings
- **Reduce** — hierarchical tree-fold along directory boundaries, detecting cross-file contradictions
- **Swap** — Agent B reads only the spec (CLAUDE.md, etc.) and checks expectations against map-phase ground truth — never reads source code

Works with any OpenAI-compatible backend or Ollama directly.

## Install

```bash
pip install garlicpress
```

Or from source:

```bash
git clone https://github.com/RALaBarge/garlicpress
cd garlicpress
pip install -e .
```

## Quick start

```bash
# Against Ollama (default)
garlicpress run /path/to/repo --spec CLAUDE.md --map-model llama3.2:3b

# Against OpenAI
OPENAI_API_KEY=sk-... garlicpress run /path/to/repo --spec CLAUDE.md \
  --base-url https://api.openai.com/v1 \
  --map-model gpt-4o --reduce-model gpt-4o --swap-model gpt-4o

# Against Anthropic (via OpenAI-compat)
OPENAI_API_KEY=sk-ant-... garlicpress run /path/to/repo --spec CLAUDE.md \
  --base-url https://api.anthropic.com/v1 \
  --map-model claude-sonnet-4-6
```

## CLI reference

### `garlicpress run` — full pipeline

```
garlicpress run REPO_PATH [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `--output` / `-o` | `findings` | Directory to write findings into |
| `--concurrency` / `-c` | `5` | Parallel map workers |
| `--map-model` | `gemma3:4b` | Model for map agents |
| `--reduce-model` | `gemma3:4b` | Model for reduce agents |
| `--swap-model` | `gemma3:4b` | Model for Agent B swap |
| `--spec` / `-s` | — | Spec file(s) for swap phase (repeatable) |
| `--skip-swap` | false | Skip Agent B — just map + reduce |
| `--changed-only` | false | Only review files changed since `--base-ref` |
| `--base-ref` | `HEAD~1` | Git ref for `--changed-only` diff base |
| `--base-url` | `http://localhost:11434` | Backend base URL |
| `--api-key` | env `OPENAI_API_KEY` | API key override |
| `--verbose` / `-v` | false | Verbose logging |

### `garlicpress map` — map phase only

```
garlicpress map REPO_PATH [--output findings] [--concurrency 5] [--model gemma3:4b]
```

### `garlicpress reduce` — reduce existing findings

```
garlicpress reduce FINDINGS_DIR [--model gemma3:4b]
```

Useful to re-run reduce after the map phase is already done.

### `garlicpress swap` — Agent B against existing findings

```
garlicpress swap FINDINGS_DIR --spec CLAUDE.md [--model gemma3:4b]
```

## Model recommendations

| Use case | Model |
|---|---|
| Fast local (Ollama) | `llama3.2:3b` — ~12s/file, clean JSON, no thinking mode |
| Quality local | `qwen3:8b`, `gemma3:12b` |
| Best results | `claude-sonnet-4-6`, `gpt-4o` |

**Ollama note:** garlicpress uses the native Ollama `/api/chat` endpoint when `--base-url` contains port `11434`, sending `think: false` to suppress extended thinking on qwen3/qwen2.5 models. Context is capped at 10240 tokens to stay within VRAM on consumer GPUs (tested on RTX 4070 12GB).

## Output structure

```
findings/
  skeleton.txt              # generated API surface (file tree + all signatures)
  beigebox/
    proxy.py.json           # per-file FileFindingsReport
    main.py.json
    backends/
      router.py.json
      _summary.json         # DirectorySummary for this directory
    _summary.json
  _summary.json             # root DirectorySummary
  _swap_report.json         # SwapReport from Agent B
```

Each `*.json` findings file contains:

```json
{
  "file": "beigebox/proxy.py",
  "summary": "...",
  "findings": [
    {
      "finding_id": "proxy-001",
      "severity": "high",
      "type": "missing_error_path",
      "location": "forward_chat_completion_stream:L142",
      "description": "...",
      "evidence": "..."
    }
  ],
  "interfaces_exported": [...],
  "interfaces_consumed": [...],
  "implicit_assumptions": [...],
  "cross_file_flags": [...]
}
```

Severity levels: `critical`, `high`, `medium`, `low`, `info`

Finding types: `missing_error_path`, `missing_auth`, `interface_mismatch`, `implicit_assumption_violated`, `security`, `logic_error`, `missing_validation`, `race_condition`, `resource_leak`, `other`

## Example results — BeigeBox codebase

Run against [BeigeBox](https://github.com/RALaBarge/beigebox) (204 source files, llama3.2:3b on RTX 4070):

```
Map 1041.7s · Reduce 219.1s · Swap 15.9s
```

| Severity | Findings |
|---|---|
| critical | 39 |
| high | 122 |
| medium | 299 |
| low | 220 |
| info | 11 |

Notable cross-file contradictions detected:
- **`harness_orchestrator.py` ↔ `agentic_scorer.py`** — `content` field assumed always present; scorer silently drops turns when missing
- **`__init__.py` / `base.py` / `openrouter.py`** — `forward()` method contract mismatches across backend implementations
- **`plugin_loader.py`** — assumes plugins always register cleanly; no handling for partial-load failures
- **`reflector.py`** — assumes LLM always returns parseable reflection; no fallback when response is malformed
- **`packet.py`** — `TaskPacket` stores sensitive data with no encryption assumption documented anywhere

## CI usage

```yaml
- name: garlicpress review
  run: |
    pip install garlicpress
    garlicpress run . --changed-only --skip-swap \
      --map-model llama3.2:3b \
      --output findings/
```

## License

MIT
