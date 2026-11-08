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
- **2.4 grader (2026-11-05):** `harness/grade.py` (+17 tests, 59 total). Usage:
  `python harness/grade.py --label <x> <raw files>` -> results/graded/*.graded.jsonl + results/summary/quality_<x>/.
  Track A: note_type, tags (Jaccard + precision/recall), action-item F1 (fuzzy match >= 0.5), due-date accuracy,
  entity F1 (+P/R), invented_tasks; field_score = mean of 5. Track B: key-fact correctness, abstention,
  hallucination, grounding; b017 (retrieval miss) expects abstention. Failed outputs score 0.
  Quality results, temperature 0 (Qwen3-4B Q4_K_M):
  | Setting | A valid | A field_score | A valid-only | B qa_score | B hallucination |
  |---|---|---|---|---|---|
  | prompt_only, no retry (Phase 1) | 48% | 34% | 70% | 96% | 0% |
  | prompt_only + retry | 80% | 54% | 68% | 96% | 0% |
  | json_object + retry | 80% | 54% | 68% | 96% | 0% |
  | json_schema + retry | 100% | **65%** | 65% | 96% | 0% |
  Paired check: on notes valid without enforcement, json_schema output is identical (no content cost);
  gains come only from rescuing failures. Model weaknesses: over-tagging (tag precision ~51%, recall 88%),
  over-extracting entities (precision ~51%, recall 99%), invented tasks on 8% of notes, note_type ambiguity
  (journal/reference/todo). Track B: 96% correct, 100% abstention, 0% hallucination, 100% grounded;
  only miss b019 (date arithmetic: said 14 days, correct 48). Track A synthetic accuracy is well below 90%
  -> per the earlier decision, NO real-notes slice needed; use a scripted robustness set later if time allows.
- **2.5 temperature sweep (built 2026-11-06):** `bash run_phase2_temperature.sh` = prompt_only & json_schema
  interleaved at temps 0/0.2/0.4/0.6/0.7 (3 repeats, seeds 43-45) + side test at 0.7 with filters off
  (`runner.py --no-filters` -> top_k 0, top_p 1, min_p 0; rows record sampling_filters/top_k/top_p/min_p).
  12 runs, ~75 min. Analysis: `harness/analyze_temperature.py` -> results/summary/phase2_temperature/
  (validity, quality via grader, hallucination, identical-output share, decision agreement, latency; 4 charts).
- **2.5 temperature results (2026-11-06, 12 runs, 1,800 graded rows, seeds 43-45):**
  | Mode | Temp | A first-try valid | A final valid | A quality | A decision agreement | A latency med | B quality / halluc. |
  |---|---|---|---|---|---|---|---|
  | prompt_only | 0.0 / 0.2 / 0.4 / 0.6 / 0.7 | 48 / 51 / 57 / 49 / 55% | 80-85% | 54-56% | 100 / 56 / 44 / 28 / 24% | 4.0-5.0 s | 96% / 0% |
  | json_schema | 0.0 / 0.2 / 0.4 / 0.6 / 0.7 | 92 / 91 / 95 / 93 / 97% | 100% | 63-65% | 100 / 64 / 40 / 16 / 16% | 3.2-3.5 s | 96% / 0% |
  Filters off at 0.7: almost no change (schema A agreement 20% vs 16%, prompt A first-try 52% vs 55%).
  **Finding: temperature costs CONSISTENCY, not correctness.** Validity and mean quality are flat across
  0-0.7 (errors are systematic, e.g. "admin" as note_type, not random). But the same note gets a different
  decision on most re-runs at 0.6+. Driver = tags (tag-set agreement 100 -> 68 -> 40 -> 24 -> 24% in schema mode);
  note_type agreement stays 88-100%, action-item count 88-96%. Track B is robust: decisions agree 100% at every
  temperature (only wording varies: identical text 100 -> 60%), 96% correct and 0% hallucination throughout.
  Recommendation: temperature 0 for extraction (reprocessing a note must give the same tags); Q&A tolerates 0.2-0.4.
  Sampling filters add little protection here: the 4B model's distribution is already peaked.
- Disk: C: was at 151 MB free on 2026-11-06 (device workspace failed to start). Moved Ollama models to
  D:\ollama\models (OLLAMA_MODELS user env var) -> C: 13.3 GB free. All Phase 4 files go on D:.
  `start_server.sh` starts llama-server with the pinned model (and closes Ollama).
- **Phase 2 complete** except the write-up (2.6). Outline for the user: `reports/phase2_writeup_outline.md`.

## Phase 3 (setup built 2026-11-06)
- Line-up (decided 2026-11-07, configs/phase3_models.yaml), all Q4_K_M GGUF from unsloth:
  | Model | Family | Released | Params | File |
  |---|---|---|---|---|
  | Qwen3-4B-Instruct-2507 | Alibaba | 2025-07 | 4.0B | 2.5 GB (C: HF cache) - Phase 1-2 anchor |
  | Gemma 4 E4B-it | Google | 2026 | 4.5B effective / 8B with per-layer embeddings | 4.98 GB, D:/models |
  | Granite 4.1 3B | IBM | 2026-04 | 3B dense | 2.1 GB, D:/models |
  | Phi-4-mini-instruct | Microsoft | 2025-02 | 3.8B | 2.49 GB, D:/models - added 2026-11-07 at user's request |
  (Phi: newest small general-purpose Phi; Phi-4-mini-reasoning variants excluded (long thinking); 2026 Phi is
  Phi-4-reasoning-vision-15B, too big for 8 GB VRAM.)
  Why: current families, ~3-4.5B effective, spread of memory footprints; Llama 3.2 3B (2024) and
  Phi-4-mini (2025) dropped as older. Optional 4th if time: Qwen3.5-4B (Mar 2026; same family as the anchor,
  multimodal, thinking must be off). Gemma 4 thinks only when <|think|> is in the system prompt (ours has none).
  Download: `bash download_phase3_models.sh` (curl, resumable). Per-model `server_args` (--jinja) in the config.
  Phase 4 idea: Granite 4.1 3B has an official BF16 GGUF (6.8 GB) -> F16 baseline without conversion, ~fits 8 GB.
- `bash run_phase3.sh` (venv active, Ollama closed, no server running): 3 rounds x models (order rotated per round),
  server restarted per model with `-np 1 -c 8192`, json_schema AND prompt_only, temperature 0, 1 retry,
  `--repeat-index` = round (seed 42+round), `--sysmon` background sampler (nvidia-smi -lms 250 + psutil RSS).
  Idle VRAM before each load -> results/raw/phase3_idle_vram.csv. ~70-90 min.
- Safety (found in mock test): stop_server waits until port 8080 is free; start_server checks the process is alive
  and /props model_path matches the expected file; runner aborts after 3 consecutive backend errors.
- Windows gotchas fixed 2026-11-07: b11954 rejects `--jinja` (chat template is default; server_args now "");
  Windows Python prints \r\n -> a stray \r became a bogus server argument -> all run scripts now `tr -d '\r'`.
- Smoke test (4 Track A notes, 3 rounds, 2026-11-07) passed for all 4 models; 100% reproducible across restarts.
  Early signals (n=4, not for quoting): Gemma decode ~52 tok/s vs 67-72 for others; Phi-4-mini wrote a 3-sentence
  summary (a003) that grammar can't block AND returned the identical output on retry (ignores feedback at t0).
  Gemma uses ~3.3 GB VRAM for a 5 GB file + 3.6 GB server RAM -> part of the model (likely per-layer embeddings)
  stays in system RAM; report VRAM and RAM side by side. Server RAM ~ mmap'd file pages for all models.
- **Phase 3 results (2026-11-07, Turbo mode, 24 runs, 1,200 graded rows; summary in results/summary/phase3_models/):**
  | Model | VRAM / RAM (GB) | Decode tok/s | Out tok A | Latency A / B (s) | A valid 1st/final (schema) | A quality | B quality | Halluc. | Invented tasks |
  |---|---|---|---|---|---|---|---|---|---|
  | Gemma 4 E4B | 3.32 / 4.91 | 50.5 | 137 | 2.84 / 1.44 | 100 / 100% | **73%** | **96%** | 0% | 4% |
  | Qwen3-4B-2507 | 3.71 / 5.25 | 64.1 | 202 | 3.38 / 1.18 | 92 / 100% | 65% | **96%** | 0% | 8% |
  | Granite 4.1 3B | **2.85** / 3.60 | **71.0** | 157 | 2.40 / 0.89 | 84 / 88% | 58% | 92% | 0% | 0% |
  | Phi-4-mini | 3.58 / 4.83 | 67.4 | 147 | 2.31 / 0.98 | 76 / 88% | 47% | 84% | **17%** | 12% |
  Per field (schema; note_type / tags / actions F1 / due / entities): Gemma 76/46/89/83/72, Qwen 64/47/78/70/63,
  Granite 56/41/73/64/54, Phi 52/41/60/33/47. Qwen matches Phase 2 exactly (65% / 96%) -> results reproducible.
  Findings: Gemma best quality despite slowest decode (terse outputs -> lower latency than Qwen). Schema mode raises
  first-try validity for every model (Gemma 56->100, Qwen 48->92, Granite 60->84, Phi 56->76) and quality for
  Gemma (+15 pts) and Qwen (+11), not Granite/Phi. Residual schema-mode errors = summary > 2 sentences (+1
  duplicate tags) - rules a grammar can't encode. Retry behaviour differs: Granite returned the IDENTICAL output
  on 3 of 4 retries (stubborn at t0); Phi rewrote but still broke the rule. Only hallucination: Phi on b022
  ("The Panchavati Express was booked") - the plan-vs-done trap. b019 date arithmetic failed by ALL four models.
  100% reproducible across server restarts for every model. Sample note: 25 items per track, deterministic ->
  a 4-point difference = 1 item; Gemma vs Qwen (8 pts) is meaningful, Granite vs Phi on Track B less so.
- Analysis: `harness/analyze_phase3.py`

## Phase 4 (setup built 2026-11-08)
- Model: Granite 4.1 3B (official BF16 GGUF 6.81 GB fits 8 GB VRAM -> true unquantized baseline on GPU).
- 11 versions (configs/phase4_models.yaml): BF16; ours plain Q8_0 Q6_K Q5_K_M Q4_K_M Q3_K_M Q2_K;
  ours with unsloth's importance matrix (imatrix_unsloth.gguf) Q4_K_M Q3_K_M Q2_K; unsloth's own Q4_K_M.
- `bash prepare_phase4.sh`: downloads BF16 + imatrix to D:/models/phase4, runs llama-quantize (temp .part files,
  skips finished). ~26 GB on D:.
- `bash run_phase4.sh`: reuses run_phase3.sh via env vars (MODELS_CFG, ROUNDS=2, MODES=json_schema, PREFIX=phase4,
  ANALYZE=harness/analyze_phase4.py). ~60-75 min.
- `bash run_phase4_kld.sh`: llama-perplexity KL divergence + same-top-token + PPL vs BF16 on the 60 notes
  (results/raw/phase4_kld.csv via harness/parse_kld.py). Independent of our grader.
- Quantization done 2026-11-08 (10 files in D:/models/phase4); quantize logs confirm imatrix variants loaded
  280 entries from unsloth's own calibration text (not our notes -> no contamination); imatrix does not change
  file size (Q2_K 1304.5 MiB / 3.22 bpw either way).
- Smoke test (4 notes, 1 round): BF16 ran at 17 tok/s with SM clock 210 MHz at 97% util and 7.5 of 8 GB VRAM ->
  Windows spilled to system RAM (earlier attempt at 16:16 reached 42 tok/s). Fix: Phase 4 uses -c 4096 for ALL
  versions (CTX env var in run_phase3.sh; longest prompt+answer ~1.6k tokens). analyze_phase4 now warns when a
  version's GPU clock is < 50% of the median (VRAM spill). Early signal (n=4, not for quoting): plain Q4_K_M lost
  ~48 pts vs BF16 (summaries > 2 sentences, failed after retry) while imatrix Q4_K_M matched BF16 -> wait for
  full run + KLD.
- **Phase 4 results (2026-11-08 full run, 22 runs, 1,100 graded rows, -c 4096, no VRAM-spill warning):**
  | Version | Size vs BF16 | VRAM GB | Decode tok/s | A quality | B quality | Halluc. | A failed after retry |
  |---|---|---|---|---|---|---|---|
  | BF16 | 100% | 6.90 | 40.9 | 61% | 92% | 0% | 8% |
  | Q8_0 | 53% | 3.93 | 62.7 | 60% | 92% | 0% | 8% |
  | Q6_K | 41% | 3.17 | 68.5 | 57% | 92% | 0% | 12% |
  | Q5_K_M | 36% | 2.84 | 73.0 | 52% | 88% | 0% | 12% |
  | Q4_K_M plain | 31% | 2.53 | 81.5 | 48% | 88% | 0% | 24% |
  | Q4_K_M imatrix | 31% | 2.52 | 80.1 | 61% | 88% | 0% | 8% |
  | Q4_K_M unsloth | 31% | 2.52 | 79.6 | 58% | 92% | 0% | 12% |
  | Q3_K_M plain | 25% | 2.16 | 79.4 | 54% | 88% | 17% (b025) | 8% |
  | Q3_K_M imatrix | 25% | 2.18 | 80.0 | 52% | 84% | 0% | 20% |
  | Q2_K plain | 20% | 1.83 | 91.4 | 25% | 24% | 0% | 8% |
  | Q2_K imatrix | 20% | 1.83 | 98.9 | 62% | 92% | 17% (b022) | 4% |
  Findings: Q8/Q6 near-lossless (-2/-4 pts) at 1.5-1.7x speed; speed gains flatten below Q4 (2.0x -> 2.2-2.4x);
  plain Q2_K COLLAPSED - on Track B it refused EVERY answerable question when valid (32% invalid), score only
  from correct abstentions; imatrix fully rescues Q2_K (62% / 92% = BF16 level at 20% size, 2.4x speed) and
  improves Q4_K_M (61 vs 48, plain fails the 2-sentence summary rule on 24% of notes). Hallucination appears only
  at <= 4 bpw (one item each). Noise: 25 items/track, 4 pts = 1 item; trust only large effects; KLD (pending,
  run 2026-11-09) is the tie-breaker for close calls (Q3 vs Q4, Q2-imat vs BF16).
- `harness/analyze_phase4.py` -> results/summary/phase4_quant/: size, bits/weight, VRAM, speed-up, quality and
  deltas vs BF16, KLD; charts quality/QA/speed vs size, KLD vs bpw, per-field heatmap. -> results/summary/phase3_models/ (speed, model/peak VRAM, validity,
  quality, hallucination, invented tasks, reproducibility across restarts, efficiency per GB / per second,
  per-field accuracy; 3 charts).
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
