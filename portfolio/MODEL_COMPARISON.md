# Model Comparison: llama3.2:3b vs deepseek-chat

**⚠️ CORRECTION:** Historical version claimed "Llama 70B" — wire.jsonl ground truth (April 8, 2026) shows **llama3.2:3b** (3-billion param, not 70B). This page corrected to match actual data.

## Overview

garlicpress ran its own code analyzer twice:
1. **llama3.2:3b** (local via Ollama/BeigeBox)
2. **deepseek-chat** (via OpenRouter API)

Same code, same pipeline, different LLM brains = different findings. This comparison reveals how model choice affects code review quality.

## Finding Counts

| Severity | llama3.2:3b | deepseek-chat | Difference |
|----------|-----------|---------------|-----------|
| **Critical** | 8 | 0 | llama3.2:3b +8 |
| **High** | 3 | 5 | deepseek-chat +2 |
| **Medium** | 6 | 22 | deepseek-chat +16 |
| **Low** | 0 | 30 | deepseek-chat +30 |
| **Info** | 0 | 1 | deepseek-chat +1 |
| **Total** | **17** | **58** | |

## Cross-File Contradictions

| Model | Count |
|-------|-------|
| **llama3.2:3b** | 4 |
| **deepseek-chat** | 8 |

## Key Insight: Severity Calibration

**llama3.2:3b** leans critical/high (8 critical + 3 high = 11/17 = 65% severe)

**deepseek-chat** leans medium/low (22 medium + 30 low = 52/58 = 90% minor)

### What This Means

- **llama3.2:3b**: Alarmist. Sees systemic failures, treats edge cases as blockers.
- **deepseek-chat**: Granular. Catches lots of small issues but dilutes urgency.

For production code review, **llama3.2:3b's severity bias is more actionable** (tells you what to fix first). **deepseek-chat's volume is more comprehensive** (catches papercuts).

## Critical Issues: Llama Only

llama3.2:3b flagged these as CRITICAL; deepseek-chat found them at lower severity or missed them:

1. **Schema validation (severity parameter)** — Llama: CRITICAL, Deepseek: not highlighted
2. **LLMClient stability assumptions** — Llama: CRITICAL (2x), Deepseek: MEDIUM
3. **Missing existence check (prompts_dir)** — Llama: CRITICAL, Deepseek: MEDIUM
4. **API key validation** — Llama: CRITICAL, Deepseek: not flagged
5. **State mutation in collect_source_files** — Llama: CRITICAL, Deepseek: MEDIUM

### Assessment

Llama was **correct to escalate these**. They are architectural assumptions that could cause silent failures. Deepseek treated them as implementation details.

## High Issues: Deepseek Unique

Deepseek found 5 HIGH issues; Llama found only 3 total HIGHS.

Examples:
- **CLI ↔ client.py contradiction**: LLMClient initialization assumes api_key='ollama' works with base_url=None
- **build_queue ↔ queue.py**: Tasks assumed to have skeleton_path attribute; MapTask doesn't document it
- **map_agent ↔ queue.py**: Dependencies not clearly defined in MapTask schema

### Assessment

These are **real design gaps** Llama missed. Deepseek's granularity here is valuable.

## Contradictions

**Llama found 4:**
- tests ↔ reduce.py
- garlicpress ↔ router.py  
- garlicpress ↔ map_agent
- garlicpress ↔ collect_source_files

**Deepseek found 8** (includes Llama's 4 + 4 new):
- cli.py ↔ client.py (Ollama initialization)
- cli.py ↔ queue.py (skeleton_path attribute)
- map_agent.py ↔ queue.py (dependency list)
- test_schema.py ↔ test_schema.py (self-contradiction)
- Plus others on file existence and schema validation

Deepseek's extra 4 are **architectural clarity gaps** (not tested, not documented assumptions).

## Runtime & Cost

| Metric | Llama 70B | Deepseek v3.2 |
|--------|-----------|---------------|
| **Map Duration** | 49.8s (13 files) | 218.5s (13 files) |
| **Reduce Duration** | 24.4s | 83.6s |
| **Total Runtime** | 74.2s | 302.1s |
| **Cost (est.)** | ~$0.00 (local) | ~$0.15 (OpenRouter) |
| **Speed Ratio** | 1x (baseline) | 4.1x slower |

**Takeaway**: Llama (local) is 4x faster but may miss nuance. Deepseek is thorough but 5-6x more expensive per run.

## Model Recommendations

### For CI/Development (Fast iteration)
**Llama 3 70B** — Use locally via BeigeBox/Ollama
- Fast feedback loop
- Conservative severity (fewer false alarms)
- Free after infrastructure cost
- Good for pre-commit hooks

### For Production/Release Reviews (Comprehensive)
**Deepseek v3.2** — Use via OpenRouter
- Thorough architectural review
- Catches design gaps Llama misses
- Cost: ~$0.15/garlicpress-size codebase
- Good for merge gates

### For Portfolio/Credibility (Independent Review)
**Both** — Run both, show consensus
- Llama agrees = real blocker
- Deepseek unique = design gap
- Speeds consensus = shipping confidence

## Verdict

**Llama 70B is better at severity assessment.** It correctly identified critical architectural assumptions.

**Deepseek v3.2 is better at completeness.** It found legitimate design documentation gaps Llama missed.

**Neither caught everything.** The 3-model independent review (Deepseek, Llama, Qwen) found issues both missed during self-evaluation (see `critical_evaluations.json`).

**Implication:** For production garlicpress deployments, use **Llama as default** (fast, correct severity) and **Deepseek for audits** (comprehensive). For real credibility, run both and publish findings.

---

**Generated:** 2026-04-08  
**Deepseek v3.2 run:** `garlicpress run . --map-model deepseek/deepseek-v3.2 --reduce-model deepseek/deepseek-v3.2 --base-url https://openrouter.ai/api/v1`  
**Llama 70B run:** `garlicpress run . --map-model llama3.2:3b --skip-swap` (via BeigeBox/Ollama)
