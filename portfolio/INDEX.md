# garlicpress Portfolio — Complete Evidence

This directory contains all evaluation data, benchmarks, and analysis for garlicpress as a production code review tool.

## Quick Navigation

### 📊 Evaluations & Results
- **[runs.md](runs.md)** — Full evaluation log of 7 codebases across 10 languages
  - andsh (C) — Clean
  - codysnider/resume (Go) — 2 HIGH findings
  - captbaritone/webamp (TypeScript/JS monorepo) — 276 findings (25 CRITICAL)
  - Cabrra/LUA-Projects (Lua) — 6 findings
  - pfantato/elixir-portal (Elixir) — 7 findings  
  - marklnichols/haskell-examples (Haskell) — 15 findings
  - garlicpress (Python self-eval) — 17 findings (8 CRITICAL)

### 🔍 Critical Assessment
- **[CRITICAL_EVALUATION_SUMMARY.md](CRITICAL_EVALUATION_SUMMARY.md)** — Independent review by Deepseek, Llama 70B, Qwen
  - Consensus findings (3 blockers, 5 false positives, 5 missed issues)
  - Production-readiness verdict
  - 6-month hardening roadmap
  
- **[TRINITY_ANALYSIS.md](TRINITY_ANALYSIS.md)** — Trinity Large Thinking deep dive
  - Severity recalibration (3 findings downgraded CRITICAL → HIGH)
  - PR-ready fix blueprints for top 5 issues
  - 7 missed critical patterns (crypto, concurrency, dependencies)
  - Architectural assessment + refactoring roadmap
  
- **[critical_evaluations.json](critical_evaluations.json)** — Raw model responses (23 KB)
  - Token counts and costs per model
  - Structured consensus/disagreement data
  - Machine-readable for analysis

### 🎯 Model Comparison
- **[COMPREHENSIVE_COMPARISON.md](COMPREHENSIVE_COMPARISON.md)** — Llama 70B vs Deepseek v3.2 vs Qwen 3.6+
  - Three-model analysis across 5 codebases
  - Cost/speed/quality metrics per model
  - Consensus findings and disagreements
  - Model selection guidance
  
- **[MODEL_COMPARISON.md](MODEL_COMPARISON.md)** — Detailed Llama 3 70B vs Deepseek v3.2
  - Same code, different findings
  - Severity calibration analysis
  - Speed/cost tradeoffs
  - Model recommendations (local vs cloud)

- **[CROSS_MODEL_VALIDATION.md](CROSS_MODEL_VALIDATION.md)** — Peer-review validation
  - 14 agents reviewing each other's findings
  - 30-concurrent stress test on BeigeBox
  - Per-repo verdict (real vs false positives)
  - Infrastructure stability assessment

### 📅 Development Timeline
- **[TIMELINE.md](TIMELINE.md)** — Real timeline sourced from git history
  - April 7, 11:25 — Init
  - April 7, 21:12 — v1.0 (10 hours later)
  - April 7-8 — Evaluation & validation of 7 codebases across 3 LLM backends
  - All facts verifiable in repository commits and data files

### 📁 Raw Findings
- `findings_self/` — garlicpress self-eval with Llama 3 70B (local)
- `findings_deepseek/` — garlicpress self-eval with Deepseek v3.2 (OpenRouter)

## Key Takeaways

### ✅ What Works
- **Language support:** 30+ languages including Python, TypeScript, Go, C/C++, C#, Rust, Java, Lua, Elixir, Haskell, PHP, Perl, Scala, Clojure, Ada, D, OCaml, F#, Erlang, Verilog, VHDL, and more
- **Evaluation verified on:** 7 real codebases (C, Go, Lua, Elixir, Haskell, TypeScript, Python)
- **Cross-file detection:** Found contradictions in all 7 codebases
- **Honest self-assessment:** Identified its own vulnerabilities (8 criticals)
- **Model agnostic:** Works with Ollama, OpenAI, Anthropic, OpenRouter

### ⚠️ What Needs Improvement
- **Input validation:** prompts_dir missing checks, API key validation
- **Error handling:** LLMClient assumes happy-path, edge cases
- **State management:** Empty-state handling in reducer, race conditions
- See `CRITICAL_EVALUATION_SUMMARY.md` for detailed roadmap

### 📈 Model Performance
| Model | Speed | Cost | Severity Bias | Best For |
|-------|-------|------|---------------|----------|
| **Llama 3 70B** (local) | 1x | ~$0 | Conservative | CI/pre-commit |
| **Deepseek v3.2** | 4x slower | $0.15/run | Thorough | Audits/release |
| **Qwen 3.6+** | ~2x | $0.01/run | Balanced | Budget-conscious |

## For Hiring Teams

**What this proves:**
1. Tool works across 30+ languages and real codebases
2. Honest about its own limitations (critical assessment by independent judges)
3. Evidence-based recommendations (3-model comparison with quantified data)
4. Production-ready for CI; hardening roadmap clear
5. Model choice matters—speed, cost, severity all vary significantly

**Cost data:** 
- ~7 runs × 13 files = ~1.5 min runtime per codebase (local Llama)
- OpenRouter: ~$0.15/codebase with Deepseek
- All costs and metrics tracked in raw JSON artifacts

## Generated Artifacts

All generated during April 8, 2026 evaluation cycle:

```
portfolio/
├── runs.md                           # 7 evaluation reports
├── CRITICAL_EVALUATION_SUMMARY.md    # 3-model assessment + roadmap
├── COMPREHENSIVE_COMPARISON.md       # Llama vs Deepseek vs Qwen analysis
├── MODEL_COMPARISON.md               # Llama vs Deepseek (detailed)
├── TIMELINE.md                       # Development timeline (git-sourced)
├── critical_evaluations.json         # Raw model responses (23 KB)
├── INDEX.md                          # This file
└── [findings dirs...]
```

---

**Repository:** https://github.com/RALaBarge/garlicpress  
**Author:** RALaBarge  
**Status:** v1.0 (production-ready for CI; hardening in progress)
