# garlicpress — Portfolio Run Log

Automated code analysis runs using [garlicpress](https://github.com/RALaBarge/garlicpress) backed by [BeigeBox](https://github.com/RALaBarge/beigebox) (local LLM proxy, Ollama/llama3.2:3b, RTX 4070).

---

## andsh — https://github.com/healeycodes/andsh

**Date:** 2026-04-07  
**Language:** C  
**Files scanned:** 4 (`src/main.c`, `src/repl.c`, `src/repl.h`, `test.sh`)  
**Model:** qwen3:4b (map) / llama3.2:3b (reduce)  
**Concurrency:** 8

### Finding Summary
| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| Info | 0 |

### Notable
- **Implicit assumption (low confidence):** `src/main.c` allocates the `Shell` struct on the stack. On platforms with constrained stack sizes this is a theoretical overflow risk. Not a bug in practice; a heap allocation would eliminate it entirely.
- **Cross-file note:** `repl.c`'s `shell_init` has no guard against the stack assumption in `main.c` — escalated to dir-level summary by reduce phase.
- **Verdict:** Clean, minimal C codebase. No bugs found.

---

## codysnider/resume — https://github.com/codysnider/resume

**Date:** 2026-04-07  
**Language:** Go  
**Files scanned:** 1 (`main.go`)  
**Runtime:** Map 49.5s · Reduce 1.6s · Swap 2.9s  
**Model:** llama3.2:3b  
**Concurrency:** 8

### Finding Summary
| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 1 |
| Low | 0 |
| Info | 0 |

### Findings

**HIGH — `main.go`: No existence check on resume file path**  
`os.ReadFile` is called on the `resumeFile` arg without first verifying the file exists or is readable. Any bad path produces an unhandled error rather than a user-friendly message.

**MEDIUM — `main.go`: Byte reader not closed after use**  
The byte reader opened for PDF generation is never explicitly closed, risking a resource leak.

**MEDIUM — `main.go`: No request authenticity validation**  
Incoming requests carry no auth/signature check — anyone who can reach the endpoint can trigger resume generation.

**Ambiguous (human review):** Resume file length not validated — no bounds check on file size before processing.

**Contradiction:** `main.go` assumes `resumeFile` exists (passed as arg) but never verifies it, which is self-referentially inconsistent with the error handling style used elsewhere.

**Verdict:** Small Go tool, minimal surface. Three actionable issues all in `main.go`. None are showstoppers but the missing file-existence check would be the first fix.

---

## captbaritone/webamp — https://github.com/captbaritone/webamp

**Date:** 2026-04-08  
**Language:** TypeScript/JavaScript (monorepo)  
**Files scanned:** 448  
**Runtime:** Map 903.5s · Reduce 186.0s · Swap 7.3s (~18 min)  
**Model:** llama3.2:3b  
**Concurrency:** 8

### Finding Summary
| Severity | Count |
|----------|-------|
| Critical | 25 |
| High | 37 |
| Medium | 87 |
| Low | 77 |
| Info | 50 |
| **Total** | **276** |

Contradictions across 73 directory summaries: **139** (52 critical, 27 high, 37 medium)

### Top Findings

**[CRITICAL] Hardcoded Algolia credentials** — `packages/skin-database/app/(modern)/scroll/algoliaClient.ts`  
API keys committed directly in source. Should be env vars.

**[CRITICAL] SQL injection** — `packages/skin-database/migrations/20251106000000_user_log_events.ts`  
Raw SQL with no parameterized placeholders. Migration added Nov 2025.

**[CRITICAL] Unimplemented stub in live rendering path** — `packages/webamp-modern/src/skin/XmlObj.ts`  
`setXmlAttr` always returns `false`, `setXmlAttributes` not implemented at all. Both called during skin load.

**[CRITICAL] Null pointer on bad skin load** — `packages/webamp-modern/src/skin/makiClasses/BitList.ts` + `MouseRedir.ts`  
Constructor assumes `uiRoot` is never null — no guard, crashes on malformed skin.

**[CRITICAL] Destructive migration** — `packages/skin-database/migrations/20220202203919_instagram_posts.ts`  
`DROP TABLE` with no schema presence check — silent data loss if schema drifted.

**[HIGH] Hardcoded DB credentials** — `packages/skin-database/migrations/20251107000000_session_tables.ts`

**[HIGH] `knex.raw()` with no error handling** — multiple migration files

### Pattern
`skin-database` package dominates criticals: missing error handling in migrations, hardcoded credentials, unguarded GraphQL resolvers. `webamp-modern` MAKI classes have multiple stub/unimplemented methods in live skin rendering paths.

### Open Issues (highest impact / lowest effort)
| # | Issue | Type | Effort |
|---|-------|------|--------|
| #1315 | `renderWhenReady` docs: `domNode` marked optional but required | Docs | Minimal — owner asked for PR |
| #485 | Tracks >100min show broken time display | Bug | Very low — ~10 line fix, help wanted |
| #1190 | EQ ON button 2px too wide, bleeds into AUTO | Bug | Low — sprite/CSS offset |
| #1251 | Use `showDirectoryPicker` instead of upload dialog | UX | Low — progressive enhancement |
| #1294 | Visualizer runs uncapped on 144hz displays | Perf | Low — standard rAF cap pattern |
| #1295 | Visualizer destroyed on mode switch | Bug | Medium — lifecycle trace |
| #1139 | `crossOrigin` hardcoded to `anonymous` | API | Medium — owner gave direction |
| #1227 | Drag+play fails on Chrome low MEI | Bug | Medium — known autoplay pattern |

---

## Cabrra/LUA-Projects — https://github.com/Cabrra/LUA-Projects

**Date:** 2026-04-08  
**Language:** Lua  
**Files scanned:** 9 (games, algorithms, Project Euler solutions)  
**Runtime:** Map 76.0s · Reduce 56.4s  
**Model:** llama3.2:3b  
**Concurrency:** 5

### Finding Summary
| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 2 |
| Medium | 2 |
| Low | 1 |
| Info | 0 |

**Cross-file contradictions:** 4

### Notable
- **CRITICAL:** Hangman game lacks input sanitization, allowing injection attacks
- **HIGH:** Battle arena assumes player defense values are valid but doesn't validate
- **HIGH:** Euler problems have overlapping calculation assumptions (sum of multiples logic)
- **Pattern:** Games and math scripts make implicit assumptions about valid inputs without guards
- **Verdict:** Educational/hobby codebase with security gaps typical of learning projects. Input validation is the main issue.

---

## pfantato/elixir-portal — https://github.com/pfantato/elixir-portal

**Date:** 2026-04-08  
**Language:** Elixir  
**Files scanned:** 5 (`mix.exs`, `portal.ex`, `door.ex`, `application.ex`, tests)  
**Runtime:** Map 20.8s · Reduce 40.6s  
**Model:** llama3.2:3b  
**Concurrency:** 5

### Finding Summary
| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 1 |
| Medium | 3 |
| Low | 2 |
| Info | 0 |

**Cross-file contradictions:** 8

### Notable
- **CRITICAL:** `mix.exs` dependency function doesn't validate dependencies or check for errors
- **HIGH:** Mix file doesn't close file descriptors or handle connection resources properly
- **MEDIUM:** Test code assumes `Portal` module exports are stable but contract not documented
- **MEDIUM:** Multiple assumptions about test helper ExUnit initialization behavior
- **Verdict:** Beginner Elixir project with typical learning curves. Missing resource management and implicit test assumptions. The cross-file contradictions highlight a gap between test expectations and actual module guarantees.

---

## marklnichols/haskell-examples — https://github.com/marklnichols/haskell-examples

**Date:** 2026-04-08  
**Language:** Haskell  
**Files scanned:** 12 (algorithms, Project Euler, functional examples)  
**Runtime:** Map 36.2s · Reduce 30.4s  
**Model:** llama3.2:3b  
**Concurrency:** 5

### Finding Summary
| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 5 |
| Medium | 9 |
| Low | 0 |
| Info | 0 |

**Cross-file contradictions:** 6

### Notable
- **CRITICAL:** `Problem5.hs` input to `smallestDivAll` is assumed valid but never validated
- **HIGH:** Fibonacci and Prime functions assume they'll be used within Project Euler context
- **HIGH:** Multiple functions expect non-empty lists but don't guard against empty input
- **PATTERN:** Pure functional code has good compositional guarantees but makes precondition assumptions across modules
- **Verdict:** Solid functional code with library-quality patterns but missing input precondition validation. Type system provides structure safety but runtime assumptions aren't documented.

---

## garlicpress (self-evaluation) — https://github.com/RALaBarge/garlicpress

**Date:** 2026-04-08  
**Language:** Python  
**Files scanned:** 10 (core pipeline: map, reduce, swap, client, config, skeleton, schema)  
**Runtime:** Map 49.8s · Reduce 24.4s  
**Model:** llama3.2:3b  
**Concurrency:** 5

### Finding Summary
| Severity | Count |
|----------|-------|
| Critical | 8 |
| High | 3 |
| Medium | 6 |
| Low | 0 |
| Info | 0 |

**Cross-file contradictions:** 4

### Top Findings

**[CRITICAL] Schema validation — `severity` parameter**  
No enum coercion for unknown severity values; assumes LLM always returns valid enum. Fallback exists but not in all paths.

**[CRITICAL] Multiple assumptions about LLMClient stability**  
`map_agent.py` assumes client always returns valid JSON; `swap.py` assumes completion is successful without error handling.

**[CRITICAL] Missing existence check on `prompts_dir`**  
`config.py` silently fails if prompt templates don't exist; no early validation.

**[HIGH] Ollama detection fragile**  
`client.py:_is_ollama()` assumes `base_url` is always a string; crashes on None or non-string input.

**[HIGH] Missing directory-level findings handling**  
`reduce.py` assumes all files in a directory have findings; silently drops missing ones.

**[MEDIUM] Skeleton truncation side effects**  
If skeleton exceeds token budget, map agents receive incomplete context without warning.

### Verdict
garlicpress is a well-architected pipeline but has edge-case vulnerabilities typical of v1.0 software:
- Needs stronger input validation boundaries (config, LLM responses)
- Cross-file assumptions about data completeness need explicit contracts
- LLM error handling assumes happy-path completions

The contradictions detected show the tool catching real issues it's designed to find — these are good targets for hardening.

---
