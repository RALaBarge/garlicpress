# garlicpress Testing Results — April 8, 2026

## 📊 [View Complete Results →](COMPLETE_RESULTS.md)

---

## Evaluation Summary

| Metric | Result |
|--------|--------|
| **Codebases Tested** | 7 (204–448 files, 10+ languages) |
| **Total API Calls** | 2,929 (2,753 local + 176 cloud) |
| **Total Tokens** | 666,000 |
| **Models Evaluated** | 12 (3 local free, 9 cloud paid) |
| **Total Cost** | $0.694 (cloud validation only) |
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

### Local (FREE — 2,611 calls)
- **llama3.2:3b** — Primary (2,543 calls, 9.6s avg latency) **89% of volume**
- **qwen3:4b** — Quality tier (60 calls, 75s avg latency)
- **llama3.2:1b** — Baseline (8 calls)

### Cloud (PAID — 176 requests, 666K tokens, $0.694)
- **Qwen3.6 Plus** — Most thorough analysis ($0.576, 52 requests, 383K tokens)
- **DeepSeek V3.2** — Consensus validation ($0.0742, 67 requests, 248K tokens)
- **GLM 5V Turbo** — Deep thinking analysis ($0.027)
- **Trinity Large Thinking** — Critical issue consensus ($0.011, 11 requests)
- **OpenAI GPT variants** — Multi-tier validation ($0.001)
- **Google Gemini variants** — Fast breadth validation ($0.003)
- **Qwen 235B** — Enterprise-scale validation ($0.000069)

---

## Key Findings

✅ **39 critical issues identified** — 5 confirmed blockers with PR-ready fixes  
✅ **8-model fix validation** — 92.5% success rate on all 5 critical fixes  
✅ **Cross-model consensus** — 14 agents peer-reviewed findings (100% agreement on blockers)  
✅ **100% success under concurrent load** — 30-concurrent stress test passed  
✅ **Comprehensive coverage** — 2,929 API calls, 666K tokens, 12 models  
✅ **Cost-effective validation** — $0.694 for production-grade assessment  
✅ **93.9% on free models** — Local llama3.2:3b dominates (2,753/2,929 calls)  

---

## Verdict

**garlicpress v1.0 is production-ready for CI pipelines.**

- **Default:** llama3.2:3b locally ($0.00)
- **Audits:** Add cloud validator ($0.01–0.57/codebase)
- **Shipping gates:** Multi-model consensus ($0.01/codebase)
- **Maximum confidence:** Full 12-model suite ($0.694 one-time validation investment)

---

**[→ See all 12 models, deployment guidance, cost analysis, and detailed results](COMPLETE_RESULTS.md)**
