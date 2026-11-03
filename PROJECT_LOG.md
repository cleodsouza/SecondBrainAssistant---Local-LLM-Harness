# SLM Second Brain Assistant - project log

Running record of decisions and results. Update at the end of each work session.

## Project
Local SLM assistant for a personal-knowledge "second brain", built in phases:
1. Measurement (TTFT, tok/s, latency) - **done 2026-10-29**
2. Structure & determinism (JSON schema, Pydantic, retry once, temperature sweep 0-0.7) - next
3. Model comparison (3 SLMs, memory / speed / quality on 50 prompts, technical report)
4. Quantization (GGUF F16 / Q8_0 / Q6_K / Q5_K_M / Q4_K_M / Q3_K_M / Q2_K, speed vs quality)

Learning mode from Phase 2: the user writes the core code (retry wrapper, validation, grade.py);
Claude gives interface + tests, explains concepts, reviews.

## Hardware & software (fixed for the whole project)
| Item | Value |
|---|---|
| Laptop | AMD Ryzen 9 6900HS, 16 GB RAM (15.2 usable) |
| GPU | NVIDIA RTX 3070 Ti Laptop, 8 GB VRAM, driver 581.08 (CUDA 13.0) |
| OS | Windows (10.0.26300), Git Bash |
| Python | 3.11.9, venv at `second_brain_corpus/.venv` |
| llama.cpp | prebuilt **b11954** (commit f1a7dea99), Windows x64 CUDA 12 + CUDA 12.4 DLLs, in `llama-bin/` |
| Old source build | `~/llama.cpp` - CPU-only (GGML_CUDA OFF); keep for `convert_hf_to_gguf.py` (Phase 4) and an optional CPU-vs-GPU data point |

## Dataset (second_brain_corpus/)
- 60 synthetic notes (fictional persona Aarav, Jul-Oct 2026), 16-296 words, median 34.
- Track A: 25 note -> `ProcessedNote` items (42 action items, 16 with due dates).
- Track B: 25 questions -> `NoteAnswer` (20 answerable, 5 unanswerable).
- Retrieval held constant: Chroma, BAAI/bge-small-en-v1.5, 1 note = 1 chunk (>200 words split), top-k 4, cosine,
  no reranking/hybrid. **recall@4 = 0.95** (19/20). Only miss: b017 (deadline aggregation) - grade it on abstention.
- Frozen contexts: `build/track_b_frozen.jsonl`, **sha256[:12] = 8b098c8ed61a**. Re-check if ever re-frozen.

## Phase 1 - baseline (2026-10-29)
Setup: Qwen3-4B-Instruct-2507 Q4_K_M (unsloth GGUF), `-ngl 99 -c 8192 --seed 42` (4 slots by default),
temperature 0, top_k 40, top_p 0.95, min_p 0.05, repeat_penalty 1.0, n_predict 512, cache_prompt false,
prompt version v1, 50 prompts x 5 repeats + 3 warm-up, order shuffled (seed 1234).
Analysis excludes the first 15 requests of each run (GPU clock ramp-up).

**Canonical baseline = run 1** (`results/raw/phase1_qwen3-4b-instruct_q4km_20261029-144931.jsonl`)

| Run | Track | TTFT median (ms) | TTFT p95 | Latency median (ms) | Latency p95 | Decode tok/s | Prefill tok/s |
|---|---|---|---|---|---|---|---|
| 1 | A | 228 | 267 | 2,978 | 3,973 | 73.4 | 2,352 |
| 1 | B | 298 | 353 | 1,021 | 1,417 | 73.0 | 2,399 |
| 2 | A | 230 | 324 | 2,991 | 4,118 | 72.9 | 2,274 |
| 2 | B | 304 | 522 | 1,101 | 1,632 | 67.7 | 2,350 |

Run 2 = `...20261029-154046.jsonl`. Median input/output tokens: A 407/199, B 559/54.

Findings
- Latency is decode-dominated: decode = 93% of Track A latency, 71% of Track B.
- TTFT ~= 33 ms + 0.46 ms per input token (+ ~60 ms client/HTTP overhead vs server prompt_ms).
- 100% of outputs parse as JSON; 0 hit the 512-token cap; temperature 0 is fully deterministic
  (identical text across all 5 repeats AND across both runs).
- GPU warmed 64 -> 82 C in run 1 with only ~0.6% decode drop (~2% dip above 80 C). Peak VRAM 3.9 GB.
- Run-to-run: decode -4.2%, prefill -2.9%, TTFT +3.2%, latency +7.1% (mostly Track B). Run 2 sat ~4% slow,
  then jumped to 83-85 tok/s near request 230 while hotter -> external interference / power state change.
  Conclusion: laptop environment noise is about +/-4-7% between sessions.

Lessons carried forward
- Use `warmup: 10` from Phase 2 on (3 was not enough for clock ramp-up).
- Start llama-server with `-np 1` for Phase 3 memory comparisons.
- Phase 3: interleave models in one session; treat speed differences < ~7% as noise unless repeated.
- GPU SM-clock samples are taken after each request (GPU idling) - not meaningful; Phase 3 sysmon.py
  will sample continuously in the background.
- Report per-track numbers; "all" medians mix 3 s and 1 s requests.
- Benchmark plugged in, Performance mode, other apps (including the Claude app) closed.

## Decisions
- 2026-11-02: **Domain stays Second Brain** (considered switching to public data, e.g. Banking77 + SQuAD 2.0;
  rejected because of training-data contamination risk, loss of controlled edge cases, and the weaker
  "private local data" story).
- Real-data slice: the user has **no personal notes of their own**. Decide after the first Phase 2 grading run:
  - synthetic Track A accuracy at temp 0 > ~90% -> collect 10-15 real notes from public digital gardens /
    Obsidian vaults (check licences) and/or friends (consent + anonymize), tag `source: real`, report separately.
  - otherwise -> skip real slice; add a scripted robustness set (typos, Hinglish, merged notes) in Phase 3/4
    and list "synthetic data only" as a limitation.

- Model provenance: Phases 1-3 use **pre-quantized** community GGUFs (Q4_K_M; pilot = unsloth's
  Qwen3-4B-Instruct-2507-Q4_K_M, possibly imatrix-calibrated). State this in the report's setup section.
  Phase 4: quantize from original BF16/F16 weights ourselves; extra comparison = own Q4_K_M vs unsloth Q4_K_M.
- Start the server offline-safe and pinned with `-m <path>` instead of `-hf`:
  `C:/Users/cleon/.cache/huggingface/hub/models--unsloth--Qwen3-4B-Instruct-2507-GGUF/snapshots/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf`

## Phase 2 progress
- 2.1 validation layer: stub `harness/validate.py` + 26 tests in `harness/tests/test_validate.py`
  **Done** (Claude wrote it after user preferred that; 26/26 pass on the user's machine).
- 2.2 retry wrapper: `harness/structured.py` (`generate_structured`, injected `generate_fn`, one retry as a
  conversation with the exact validation errors, typed `FailedOutput`) + 9 tests in `tests/test_structured.py`.
  Demo: `python harness/structured.py a001 a008 b021 [--temp 0.7]`.
- 2.3 enforcement modes: `harness/enforcement.py` (prompt_only / json_object / json_schema via llama-server
  `json_schema` request field; Track B schema also bounds chunk ids 0..k-1). Runner now runs every item through
  `generate_structured` (rows add status, n_attempts, first/final error type, retry latency, total latency,
  final_output; top-level timings = attempt 1). CLI overrides: --temperature --enforcement --max-retries.
  Config `configs/phase2_base.yaml` (repeats 3, warmup 10, max_retries 1). Sweep: `bash run_phase2_enforcement.sh`
  (3 modes x temps 0.0/0.7, ~35 min). Analysis: `harness/analyze_phase2.py --label <x> <files>`
  -> results/summary/phase2_<x>/ (summary.md/csv, error_examples.md, 3 charts).
  Grammar cannot enforce: summary <= 2 sentences, answerable=false => answer=null (validator still catches).
- 2.3 smoke test (2026-11-02) found a bug: enforcement._clean stripped the FIELDS named title/description
  from the grammar schema -> json_schema failed 100%. Fixed + tests/test_enforcement.py (42 tests total).
- **2.3 enforcement results (2026-11-03, Qwen3-4B Q4_K_M, 50 items x 3 repeats, 1 retry)**
  Files: results/raw/phase2_*20261103-08*/09*.jsonl; summary in results/summary/phase2_enforcement/.
  | Mode | Track A first-try valid | A rescued by retry | A final valid | A total latency med | Track B |
  |---|---|---|---|---|---|
  | prompt_only | 48% | 62% | 80% | 4.9 s | 100% valid, ~1.0 s |
  | json_object | 48% | 62% | 80% | 5.0 s | 100% valid |
  | json_schema | **92%** | 100% | **100%** | **3.0 s** | 100% valid, decode ~3% slower |
  Track A attempt-1 errors (prompt_only, t0): note_type outside enum (18), tags outside vocab (18),
  summary > 2 sentences (6), malformed due date (3). Final failures: a005 a010 a013 a022 a024.
  json_schema residual errors = rules a grammar can't express: duplicate tags (3), summary > 2 sentences (3).
  json_object identical to prompt_only: the model already emits parseable JSON; errors are wrong VALUES.
  Phase 1's "100% parseable JSON" hid a ~52% schema-failure rate on Track A.
  Retry nearly doubles Track A median latency (2.9 s -> 4.9 s); schema enforcement avoids that cost.
- **Design flaw found:** seed was fixed at 42 for every request, so temperature 0.7 repeats were identical
  (1 distinct output per item) -> the t0.7 runs are ONE sample each, not a variability measurement.
  Fixed: runner now uses seed = base + repeat (`vary_seed_per_repeat`, default true; seed stored per row).
  Temperature effects will be measured properly in step 2.5. Enforcement comparison at t0 is valid as-is.
- Run scripts now refuse to start outside the venv (the 2026-11-03 runs used system Python 3.9 -> the analysis
  step crashed on pandas/numpy; model outputs unaffected).
- Working mode (agreed 2026-11-02): Claude writes code and explains it; after each piece the user does a short
  "own it" exercise (modify / break-and-fix). User decides design choices; user writes the report, Claude
  reviews. Goal: forward-deployed-engineer skills (own, debug, explain AI-written code).

## Next steps
- Phase 2: system prompts already in `harness/prompts.py` (v1). Build: enforcement modes (prompt-only /
  JSON mode / JSON-schema grammar), validation + one retry with the Pydantic error, typed failure,
  grade.py (Track A field metrics; Track B key facts, grounding, abstention), temperature sweep
  0 / 0.2 / 0.4 / 0.6 / 0.7 x 5 runs, plus a side experiment with sampling filters off at 0.4 and 0.7.
