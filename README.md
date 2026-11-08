# Second Brain Assistant — Local SLM Benchmarking & Reliability Harness

A private, on-device notes assistant built on small language models (3–4B parameters) running locally with
llama.cpp on a consumer laptop GPU — used as a testbed to **measure, harden and compare** local LLM inference:
speed, structured-output reliability, correctness, model choice and quantization.

**Hardware:** ASUS ROG Zephyrus G15 · RTX 3070 Ti Laptop GPU (8 GB) · Ryzen 9 6900HS · 16 GB RAM · Windows ·
llama.cpp **b11954** (CUDA 12.4) · Python 3.11

---

## Headline findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **Parseable JSON ≠ valid output.** 100% of outputs parsed as JSON, but only **48%** matched the schema on note extraction. | Phase 2 |
| 2 | **Grammar-constrained decoding beats repair.** Compiling the Pydantic schema to a GBNF grammar raised first-try validity 48% → **92%**, final validity 80% → **100%**, quality 54% → 65%, and *cut* median latency 4.9 s → 3.0 s by avoiding retries — with no content cost on items already valid. | Phase 2 |
| 3 | **Temperature costs consistency, not correctness.** Quality was flat from 0 to 0.7, but the same note received the same tags/type/task-count on only **16%** of re-runs at 0.6+. Use temperature 0 for extraction. | Phase 2 |
| 4 | **Decode speed ≠ response time.** Gemma 4 E4B decodes 20% slower than Qwen3-4B yet answers faster because it writes ~30% fewer tokens — and scores best (73% vs 65%, 96% Q&A, 0% hallucination). | Phase 3 |
| 5 | **A grammar fixes format, not judgment.** Schema mode raised validity for all 4 models, but quality only for the stronger two; retries helped some models and were useless for others (Granite repeated identical output). | Phase 3 |
| 6 | **Calibration is the decisive quantization choice.** An importance matrix cut KL divergence 2.5–4× at equal size; uncalibrated Q2_K collapsed (refused every answerable question), calibrated Q2_K matched BF16 task scores at 20% of the size and 2.4× speed. | Phase 4 |
| 7 | **Small task benchmarks can hide degradation.** Calibrated Q2_K tied BF16 on our 50 tasks but agreed with its top token only 72% of the time — pair task scores with a distribution metric (KLD). | Phase 4 |

---

## Phases

### Phase 1 — Measurement (Qwen3-4B-Instruct-2507, Q4_K_M)
Streaming harness measuring TTFT, prefill/decode throughput, end-to-end latency, token counts and GPU state,
with prompt caching off, warm-ups excluded, shuffled order and pinned sampling. 500 requests, two runs.

| Track | TTFT median | Latency median | Decode |
|---|---|---|---|
| A — note processing | 228 ms | 2.98 s | 73.4 tok/s |
| B — Q&A over notes | 298 ms | 1.02 s | 73.0 tok/s |

Latency is decode-bound (93% of Track A time); TTFT ≈ 0.46 ms per input token; outputs byte-identical across
repeats at temperature 0; laptop run-to-run noise ±4–7%.

### Phase 2 — Structure & determinism
Pydantic validation (empty / not-JSON / schema / context errors), **one error-guided retry** as a continued
conversation, typed failure objects, three enforcement modes (prompt-only, generic JSON grammar, schema grammar),
a grader for correctness, and a temperature sweep (0–0.7, per-repeat seeds, sampling filters on/off).

| Setting (temp 0) | Note validity | Note quality | Latency | Q&A correct | Hallucination |
|---|---|---|---|---|---|
| Prompt only, no retry | 48% | 34% | ~2.9 s | 96% | 0% |
| Prompt only + retry | 80% | 54% | 4.9 s | 96% | 0% |
| Generic JSON + retry | 80% | 54% | 5.0 s | 96% | 0% |
| **Schema grammar + retry** | **100%** | **65%** | **3.0 s** | 96% | 0% |

### Phase 3 — Model comparison (4 families, Q4_K_M, interleaved rounds, background memory sampling)
| Model | VRAM | Decode | Note latency | Note quality | Q&A | Hallucination |
|---|---|---|---|---|---|---|
| **Gemma 4 E4B** (Google) | 3.3 GB | 50 tok/s | 2.8 s | **73%** | **96%** | 0% |
| Qwen3-4B-Instruct-2507 (Alibaba) | 3.7 GB | 64 tok/s | 3.4 s | 65% | **96%** | 0% |
| Granite 4.1 3B (IBM) | **2.85 GB** | **71 tok/s** | 2.4 s | 58% | 92% | 0% |
| Phi-4-mini-instruct (Microsoft) | 3.6 GB | 67 tok/s | 2.3 s | 47% | 84% | 17% |

### Phase 4 — Quantization (Granite 4.1 3B, 11 versions from official BF16)
| Version | Size | Decode | Note quality | Q&A | KLD vs BF16 | Same top token |
|---|---|---|---|---|---|---|
| BF16 | 6.81 GB | 41 tok/s | 61% | 92% | 0 | 100% |
| Q8_0 | 53% | 63 tok/s | 60% | 92% | 0.002 | 97.9% |
| Q6_K | 41% | 69 tok/s | 57% | 92% | 0.010 | 94.5% |
| Q4_K_M plain | 31% | 82 tok/s | 48% | 88% | 0.091 | 83.5% |
| **Q4_K_M calibrated** | 31% | 80 tok/s | **61%** | 88% | **0.036** | 90.7% |
| Q2_K plain | 20% | 91 tok/s | 25% | 24% | 1.241 | 50.6% |
| Q2_K calibrated | 20% | 99 tok/s | 62% | 92% | 0.320 | 72.1% |

Full table (incl. Q5_K_M, Q3_K_M, unsloth's Q4_K_M) in `results/summary/phase4_quant/summary.md`.
**Recommendation:** calibrated Q4_K_M as the sweet spot; Q6_K for near-zero drift; never uncalibrated ≤ 4 bits.

---

## Dataset
Synthetic personal-knowledge corpus (fictional persona, Jul–Oct 2026): **60 notes** with recurring threads,
edge cases (Hinglish, shorthand, vague dates, no-action notes, a long note) and **50 labelled items**:
- **Track A (25):** note → `ProcessedNote` (type, tags, summary, action items with resolved due dates, entities)
- **Track B (25):** question + 4 retrieved chunks → `NoteAnswer` (answerable flag, answer, cited chunks, confidence),
  including **5 unanswerable questions** built as hallucination traps (e.g. a *planned* train booking).

Retrieval is held constant and frozen once (ChromaDB, `BAAI/bge-small-en-v1.5`, top-4, recall@4 = 0.95), so
every model and setting sees byte-identical context.

## Harness design (why it is built this way)
- **Validation separates syntax / schema / context errors** — each is its own metric and needs different feedback.
- **The model call is injected** (`generate_fn`), so retry logic is unit-tested with a fake model and the same
  wrapper runs against any backend.
- **Retry = continued conversation with the exact validation errors**, fixed budget of one; failure is a typed value, never an exception.
- **Fairness controls:** prompt cache off, warm-ups excluded, shuffled order, pinned sampling, seed = base + repeat,
  interleaved model rounds, server restart per model with `/props` model-file verification.
- **Smoke tests before every long run** caught real problems: a grammar-cleaning bug (schema mode failed 100%),
  a fixed-seed flaw (temperature repeats identical), a server-switch race, Windows `\r\n` corrupting arguments,
  and BF16 silently spilling out of VRAM (now auto-flagged).
- **59 unit tests** (`harness/tests/`).

## Repository layout
```
second_brain_corpus/   notes, labelled Track A/B items, Pydantic schemas, build + retrieval-freeze scripts
harness/               runner, prompts, validate, structured (retry), enforcement, grade, sysmon, analysis scripts
  tests/               59 pytest tests
configs/               one YAML per experiment / model line-up
results/raw/           one JSONL row per generation (never edited) + run metadata + memory samples
results/graded/        graded rows
results/summary/       tables, charts, error examples per phase
reports/               write-up outlines per phase
run_phase*.sh          one script per experiment; prepare_phase4.sh builds the quantized models
```

## Reproduce
```bash
# environment
python -m venv second_brain_corpus/.venv && source second_brain_corpus/.venv/Scripts/activate
pip install -r harness/requirements.txt chromadb sentence-transformers
python second_brain_corpus/build_corpus.py && python second_brain_corpus/freeze_contexts.py
python -m pytest harness/tests -q

# llama.cpp: Windows CUDA 12 build + CUDA 12.4 DLLs in ./llama-bin
bash start_server.sh                    # Phase 1-2 server (pinned Qwen3-4B Q4_K_M)
bash run_phase1.sh                      # Phase 1
bash run_phase2_enforcement.sh          # Phase 2.3
bash run_phase2_temperature.sh          # Phase 2.5
python harness/grade.py --label t0 results/raw/phase2_*_t0.0_*.jsonl

bash download_phase3_models.sh && bash run_phase3.sh          # Phase 3 (manages its own servers)
bash prepare_phase4.sh && bash run_phase4.sh && bash run_phase4_kld.sh
python harness/analyze_phase4.py results/raw/phase4_granite-*.jsonl
```
Model files live outside the repo (`D:/models`, Hugging Face cache); paths are set in `configs/*.yaml`.

## Limitations
- 50 synthetic items from a single annotator — 4 points = 1 item; only large differences are meaningful.
  Note-type and tag labels involve judgment; due dates and Q&A answers are firmer.
- One laptop, one runtime (llama.cpp on Windows); timings carry ±4–7% session noise.
- Grader uses fuzzy matching for action items and substring matching for key facts; titles/summaries are not graded.
- Phase 4 covers one 3B model; larger models usually tolerate quantization better.
