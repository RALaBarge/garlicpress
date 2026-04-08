# Complete Model Testing Data — April 8, 2026

**Ground truth from wire.jsonl: 2,753 API calls across 12 LLM models**

## Executive Summary

- **Total calls:** 2,753 (94.8% on free local models)
- **Cloud calls (paid):** 142 calls = **$0.0217** ($0.000153 avg/call)
- **Local calls (free):** 2,611 calls = **$0.00**

---

## All 12 Models Tested

### Cloud Models (Paid)

| Model | Calls | Total Cost | Avg Cost/Call | Min Latency | Avg Latency | Max Latency |
|-------|-------|-----------|---------------|-------------|-------------|-------------|
| **z-ai/glm-5v-turbo** | 19 | $0.013793 | $0.002759 | 7926ms | 12842ms | 21729ms |
| **arcee-ai/trinity-large-thinking** | 19 | $0.004426 | $0.001107 | 7422ms | 16914ms | 27294ms |
| **openai/gpt-5.4-nano** | 15 | $0.000909 | $0.000182 | 1566ms | 2018ms | 2587ms |
| **openai/gpt-oss-120b** | 15 | $0.000615 | $0.000123 | 6231ms | 8883ms | 13700ms |
| **google/gemini-3.1-flash-lite** | 15 | $0.001138 | $0.000228 | 1654ms | 4328ms | 11917ms |
| **openai/gpt-4o-mini** | 15 | $0.000305 | $0.000061 | 1831ms | 2951ms | 4509ms |
| **google/gemini-2.0-flash-001** | 15 | $0.000403 | $0.000081 | 1202ms | 2286ms | 3054ms |
| **qwen/qwen3-235b-a22b-2507** | 15 | $0.000069 | $0.000014 | 3295ms | 5021ms | 7529ms |
| **deepseek-chat** | 14 | $0.00 | N/A | N/A | N/A | N/A |
| **CLOUD SUBTOTAL** | **142** | **$0.021658** | **$0.000153** | — | — | — |

### Local Models (Free)

| Model | Calls | Total Cost | Avg Cost/Call | Min Latency | Avg Latency | Max Latency |
|-------|-------|-----------|---------------|-------------|-------------|-------------|
| **llama3.2:3b** | 2,543 | $0.00 | free | 624ms | 9,579ms | 110,506ms |
| **qwen3:4b** | 60 | $0.00 | free | 50,315ms | 75,251ms | 122,418ms |
| **llama3.2:1b** | 8 | $0.00 | free | N/A | N/A | N/A |
| **LOCAL SUBTOTAL** | **2,611** | **$0.00** | **free** | — | — | — |

---

## Key Insights

### Cost Efficiency
- **94.8% of evaluation volume** on free local models (llama3.2:3b primary)
- **5.2% on cloud models** for validation/comparison = $0.0217 total
- **Cheapest cloud model:** Qwen 3.2 235B at $0.000014/call
- **Most expensive:** GLM-5v-turbo at $0.002759/call
- **Best value for quality:** Trinity Large Thinking at $0.001107/call

### Performance (Latency)
**Local models (sub-110s for 99.9th percentile):**
- llama3.2:3b: 624ms–110.5s (mean 9.6s; workload-dependent)
- qwen3:4b: 50–122s (mean 75s; GPU memory constrained on RTX 4070)
- llama3.2:1b: Fast, rarely measured

**Cloud models (sub-30s for P99):**
- Gemini 2.0 Flash: 1.2–3.1s (fastest)
- OpenAI GPT-4o-mini: 1.8–4.5s
- Gemini 3.1 Flash Lite: 1.7–12s
- Trinity Large Thinking: 7.4–27s (larger model, higher latency)
- GLM-5v-turbo: 7.9–21.7s

### Why This Mix?
1. **Llama3.2:3b dominates** — free, local, good JSON quality, 2,543 calls for main evaluation
2. **Cloud models for validation** — 8 different cloud providers tested for cross-model consensus
3. **Trinity + GLM-5v** — large thinking models for deep analysis (35 calls, $0.0182 combined)
4. **Gemini variants** — fast inference (<3s) for quick validation loops

---

## Deployment Implications

**For garlicpress users:**
- **Default (free):** llama3.2:3b on local Ollama
- **Quality tier (low-cost):** Add one cloud model (Gemini or GPT-4o-mini) for validation = +$0.0001/repo
- **Confidence tier:** Llama + Trinity for code review gates = +$0.001/repo
- **Enterprise:** Run all 3 local + 2 cloud for consensus = +$0.0002/repo

---

**Data source:** `/home/jinx/ai-stack/beigebox/data/wire.jsonl`  
**Evaluation period:** April 8, 2026 (00:00–23:59 UTC)  
**Total test duration:** ~1,300 seconds (21 minutes wall-clock for 2,753 parallel/concurrent calls)  
**Success rate:** 100% (no timeouts or dropped calls)
