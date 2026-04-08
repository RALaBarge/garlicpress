# garlicpress Testing Results — April 8, 2026

## 📊 [View Complete Results →](COMPLETE_RESULTS.md)

---

## Evaluation Summary

| Metric | Result |
|--------|--------|
| **Codebases Tested** | 7 (204–448 files each) |
| **Total API Calls** | 2,753 |
| **Models Evaluated** | 12 (3 local free, 9 cloud paid) |
| **Total Cost** | $0.0217 (cloud validation only) |
| **Success Rate** | 100% (0 crashes, 0 timeouts) |

### Findings

| Severity | Count |
|----------|-------|
| **Critical** | 39 |
| **High** | 122 |
| **Medium** | 299 |
| **Low** | 220 |
| **Info** | 11 |
| **Cross-file Contradictions** | 139 |

---

## Models Tested

### Local (Free)
- **llama3.2:3b** — Primary (2,543 calls, 9.6s avg latency)
- **qwen3:4b** — Quality tier (60 calls, 75s avg latency)
- **llama3.2:1b** — Baseline (8 calls)

### Cloud (Paid — $0.0217 total)
- **z-ai/glm-5v-turbo** — Deep analysis ($0.0138)
- **arcee-ai/trinity-large-thinking** — Consensus validation ($0.00443)
- **openai/gpt-5.4-nano** — Fast validation ($0.000909)
- **openai/gpt-oss-120b** — Broad evaluation ($0.000615)
- **google/gemini-3.1-flash-lite** — Flexible validation ($0.00114)
- **openai/gpt-4o-mini** — Budget validation ($0.000305)
- **google/gemini-2.0-flash** — Fastest cloud ($0.000403)
- **qwen/qwen3-235b-a22b-2507** — Cheapest cloud ($0.000069)
- **deepseek-chat** — Baseline comparison

---

## Key Findings

✅ **39 critical issues identified** — 5 confirmed blockers with PR-ready fixes  
✅ **8-model fix validation** — 92.5% success rate on all 5 critical fixes  
✅ **Cross-model consensus** — 14 agents peer-reviewed findings (100% agreement on blockers)  
✅ **100% success under load** — 30-concurrent stress test passed (0 crashes)  
✅ **94.8% on free models** — Local llama3.2:3b dominates (2,611/2,753 calls)  
✅ **Production-ready** — Ready for CI; hardening roadmap in progress

---

## Verdict

**garlicpress v1.0 is production-ready for CI pipelines.**

- **Default:** llama3.2:3b (free, 9.6s avg, correct severity)
- **Audits:** Add one cloud model for validation (~$0.001/codebase)
- **Shipping gates:** Use llama3.2:3b + Trinity consensus (~$0.0011/codebase)

---

**[→ See all 12 models, deployment guidance, cost analysis, and detailed results](COMPLETE_RESULTS.md)**
