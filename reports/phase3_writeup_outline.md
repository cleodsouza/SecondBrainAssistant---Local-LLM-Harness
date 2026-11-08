# Phase 3 write-up — outline (model comparison)

Skeleton for **you** to write in your own words (2–3 pages). Numbers: 4 models, Q4_K_M GGUF each,
llama.cpp b11954, RTX 3070 Ti Laptop (8 GB), Turbo mode, temperature 0, one retry, `-np 1 -c 8192`,
50 items × 3 rounds × 2 modes = 1,200 graded outputs. Summary: `results/summary/phase3_models/summary.md`.

---

## 3.1 Goal (1 paragraph)
- Which small model is the best fit for a private, on-device notes assistant on an 8 GB laptop GPU —
  judged on speed, memory, structured-output reliability and correctness, under identical conditions?

## 3.2 Models and why (table)
| Model | Maker | Released | Size | Why included |
|---|---|---|---|---|
| Qwen3-4B-Instruct-2507 | Alibaba | Jul 2025 | 4B | Phase 1–2 anchor |
| Gemma 4 E4B | Google | 2026 | 4.5B effective (8B incl. per-layer embeddings) | Newest generation |
| Granite 4.1 3B | IBM | Apr 2026 | 3B | Smallest; instruction-following focus |
| Phi-4-mini-instruct | Microsoft | Feb 2025 | 3.8B | Newest small general-purpose Phi |
- All Q4_K_M from the same uploader (unsloth); same build, prompts, frozen contexts, sampling.

## 3.3 Method (½ page) — the fairness controls are the point
- Server restarted per model with `-np 1`; **model file verified via /props** before each run.
- **Interleaved rounds** with rotated order (round 1: A B C D, round 2: B C D A …) so heat / background
  load is spread across models — Phase 1 showed ±4–7% session noise.
- **Background memory sampler** (nvidia-smi every 250 ms + server RSS): model VRAM = after load minus
  before start; RAM reported too (Gemma keeps part of its weights in system RAM).
- Same grader as Phase 2; schema mode (main) and prompt-only (instruction-following without a grammar).

## 3.4 Results — speed and memory (schema mode)
| Model | VRAM / RAM (GB) | Decode tok/s | Output tokens (notes) | Latency notes / Q&A |
|---|---|---|---|---|
| Gemma 4 E4B | 3.32 / 4.91 | 50.5 | 137 | 2.84 / 1.44 s |
| Qwen3-4B | 3.71 / 5.25 | 64.1 | 202 | 3.38 / 1.18 s |
| Granite 4.1 3B | 2.85 / 3.60 | 71.0 | 157 | 2.40 / 0.89 s |
| Phi-4-mini | 3.58 / 4.83 | 67.4 | 147 | 2.31 / 0.98 s |
Figure: `results/summary/phase3_models/model_comparison_bars.png`
Point to make: **decode speed ≠ response time.** Gemma decodes ~20% slower than Qwen but answers faster
because it writes ~30% fewer tokens. Output length is a model property worth measuring.

## 3.5 Results — reliability and quality
| Model | Valid 1st try (prompt → schema) | Notes quality | Q&A correct | Hallucination | Invented tasks |
|---|---|---|---|---|---|
| Gemma 4 E4B | 56% → 100% | **73%** | **96%** | 0% | 4% |
| Qwen3-4B | 48% → 92% | 65% | **96%** | 0% | 8% |
| Granite 4.1 3B | 60% → 84% | 58% | 92% | 0% | 0% |
| Phi-4-mini | 56% → 76% | 47% | 84% | **17%** | 12% |
Figures: `quality_vs_latency.png`, `track_a_fields.png`
Points to make:
- Gemma best overall; Qwen reproduced its Phase 2 numbers exactly (65% / 96%) → pipeline is stable.
- Schema enforcement raises validity for **every** model, and quality for Gemma (+15) and Qwen (+11) but not
  Granite / Phi — **a grammar fixes format, not judgment.**
- All residual schema-mode failures = summary > 2 sentences (a rule no grammar can express).
- **Retry effectiveness is model-dependent:** Granite returned the *identical* output on 3 of 4 retries
  (deterministic at t=0); Phi rewrote but broke the same rule again.
- **Only hallucination:** Phi on b022 — "The Panchavati Express was booked" when the note only planned to
  book. The dataset's plan-vs-done trap worked.
- **Shared blind spot:** all four models failed b019 (days until the race) — date arithmetic at this size.
- Field view: Gemma leads on action items (89%) and due dates (83%); Phi weakest on due dates (33%).

## 3.6 Recommendation (1 paragraph — your call, defend it)
- Default: **Gemma 4 E4B** (quality, no hallucination, fast responses); memory-constrained: **Granite 4.1 3B**
  (2.85 GB, fastest decode, no invented tasks); avoid Phi-4-mini for grounded Q&A.

## 3.7 Limitations
- 25 items per track, deterministic outputs → 4 points = 1 item; Gemma vs Qwen (8 pts) meaningful, smaller gaps not.
- One quantization (Q4_K_M) from one uploader; a model's ranking can change at other precisions (Phase 4).
- Server RAM includes memory-mapped file pages, so it overstates true CPU-resident weights.
- Turbo mode for Phase 3 vs unrecorded mode in Phases 1–2: compare speeds within a phase, not across.
