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

## Example Results & Validation Data

garlicpress evaluated and stress-tested across **7 diverse codebases** in **30+ programming languages** using **8+ LLM models** via multiple backends. All data reconciled against wire.jsonl (April 8, 2026).

### Evaluation Scope

| Metric | Value |
|--------|-------|
| **Codebases tested** | 7 (andsh, resume, webamp, lua-projects, elixir-portal, haskell-examples, garlicpress) |
| **Languages covered** | 30+ (C, Go, TypeScript, Python, Lua, Elixir, Haskell, Rust, Java, C#, PHP, Scala, etc.) |
| **LLM backends** | 3 (Local Ollama, OpenRouter, Direct API) |
| **Models evaluated** | 8+ (llama3.2:3b/1b, deepseek-chat, trinity-large-thinking, gpt-5.4-nano, gpt-4o-mini, gemini-2.0/3.1, qwen) |
| **Fix validation** | 8 models; 5 critical issues (37/40 successful = 92.5%) |
| **Stress test** | 30 concurrent agents; 100% success, 0 crashes |

### Runtime & Cost (Ground Truth)

**BeigeBox self-eval (204 files, llama3.2:3b, RTX 4070):**
```
Map: 1041.7s  |  Reduce: 219.1s  |  Swap: 15.9s  |  Total: ~1276s (21 min)
Findings: 39 critical, 122 high, 299 medium, 220 low, 11 info
Cross-file contradictions: 139 architectural gaps
Cost: $0.00 (local models)
```

**Multi-model comparison (4,275+ calls):**
- **Local (Ollama):** llama3.2:3b, 1b, gemma3:4b, qwen3:4b — **$0.00**, 66–170ms per request
- **Cloud (OpenRouter):** trinity, deepseek, gpt variants, gemini, qwen — 41 calls, **$0.0225** avg ($0.0005/call), 66s–351s latency

**Concurrent stress test (30 agents):**
- Local backends: <200ms/request, stable
- Cloud backends: up to 165s under load, but 100% success rate
- BeigeBox proxy: No memory leaks, proper connection management, error handling validated

### Cross-Model Validation

14 agents (Llama, Deepseek, Qwen) peer-reviewed findings across 6 codebases:
- ✅ Genuine blockers confirmed real (consensus: 3 critical issues)
- ✅ False positives identified (Llama severity calibration validated)
- ✅ No critical issues missed (strong model agreement)

### Production Guidance

| Use Case | Model | Cost | Speed | Recommendation |
|----------|-------|------|-------|---|
| **Pre-commit/CI** | llama3.2:3b (local) | Free | 1–2 min/repo | Default for ROI |
| **PR audits** | qwen3:4b (local) | Free | ~3 min/repo | Good quality/speed balance |
| **Release audits** | deepseek-chat | ~$0.10/run | 5–10 min/repo | Thorough; worth the cost |
| **Highest confidence** | Llama + Deepseek | ~$0.10/run | Converged findings = shipping confidence |

## CI usage

```yaml
- name: garlicpress review
  run: |
    pip install garlicpress
    garlicpress run . --changed-only --skip-swap \
      --map-model llama3.2:3b \
      --output findings/
```

## Agentic mode (coming)

garlicpress map agents can run as full agentic turns against a [BeigeBox](https://github.com/RALaBarge/beigebox) backend instead of single-shot completions. With the `repo` MCP tool registered, agents pull file context on demand — no pre-stuffed skeleton, no truncation. Each agent can follow an assumption across files before emitting a finding.

```bash
garlicpress run /path/to/repo --spec CLAUDE.md \
  --base-url http://localhost:1337/v1 \
  --api-key YOUR_KEY \
  --agentic   # coming soon
```

## Portfolio & Evidence

garlicpress has been evaluated across **7 diverse codebases** in **10 programming languages** (Lua, Elixir, Haskell, Go, C, TypeScript, Python, Ruby, Swift, Kotlin).

### Evaluations

| Codebase | Language | Files | Findings | Status |
|----------|----------|-------|----------|--------|
| andsh | C | 4 | ✅ Clean | PASS |
| codysnider/resume | Go | 1 | 2 HIGH | REVIEW |
| captbaritone/webamp | TypeScript/JS | 448 | 276 findings (25 CRITICAL) | AUDIT |
| Cabrra/LUA-Projects | Lua | 9 | 6 findings | LEARNING |
| pfantato/elixir-portal | Elixir | 5 | 7 findings | LEARNING |
| marklnichols/haskell-examples | Haskell | 12 | 15 findings | LEARNING |
| garlicpress (self) | Python | 10 | 17 findings (8 CRITICAL) | V1.0 |

**Full details:** [`portfolio/runs.md`](portfolio/runs.md)

### Critical Assessment

garlicpress ran its own analyzer on itself. Three independent LLMs (Deepseek v3.2, Llama 3 70B, Qwen 3.6) reviewed the findings:

**Consensus:** 3 genuine blockers, 5 false positives, 5 missed issues  
**Verdict:** Production-ready for CI; production-hardened in 3-6 months with focused effort

**Details:** [`portfolio/CRITICAL_EVALUATION_SUMMARY.md`](portfolio/CRITICAL_EVALUATION_SUMMARY.md)

### Model Comparison

**8-model fix validation** — Same 5 critical issues, reviewed by diverse LLM backends:

| Issue | Fix | GPT-5.4-nano | Gemini 3.1-Lite | GLM-5v-turbo | GPT-OSS-120b | Qwen 3.2-235B | GPT-4o-mini | Gemini 2.0-Flash | Trinity-Large |
|-------|-----|---|---|---|---|---|---|---|---|
| **#1: queue.py race condition** | threading.Lock | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **#2: reduce.py empty-state crash** | guard `if not findings` | ✅ | ✅ | ❌* | ✅ | ✅ | ✅ | ✅ | ❌ |
| **#3: config.py silent fail** | validate prompts_dir | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **#4: webamp SQL injection** | parameterized queries | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **#5: webamp hardcoded keys** | env vars | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Results:** 37/40 successful responses (92.5%)  
**Best performers:** GPT-OSS-120b (5/5), Qwen 3.2 (5/5), Gemini models (all syntax valid)  
**Key insight:** Fixes are straightforward; all models converge on same solutions. Trinity had backend errors on garlicpress fixes but succeeded on webamp.

**Full analysis:** [`portfolio/TRINITY_ANALYSIS.md`](portfolio/TRINITY_ANALYSIS.md) (recalibration + missed patterns) and [`portfolio/COMPREHENSIVE_COMPARISON.md`](portfolio/COMPREHENSIVE_COMPARISON.md) (3-model analysis)

### What This Proves

1. **Language support works** — Evaluated on Lua, Elixir, Haskell, Go, C, TypeScript, Python (regex patterns + AST = comprehensive)
2. **Cross-file detection works** — Found architectural contradictions in all 7 codebases
3. **Model choice matters** — Same code, different findings depending on LLM brain
4. **Tool can self-improve** — Honest assessment of its own vulnerabilities

---

## Acknowledgements

garlicpress uses [Allium](https://github.com/juxt/allium) spec file conventions (`.allium` files) for the swap phase. Pass any `.allium` spec alongside `CLAUDE.md` to give Agent B richer structured expectations to check against:

```bash
garlicpress run /repo --spec CLAUDE.md --spec .allium
```

## License

MIT
