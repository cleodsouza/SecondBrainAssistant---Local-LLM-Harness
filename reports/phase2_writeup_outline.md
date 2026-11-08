# Phase 2 write-up — outline

This is a skeleton for **you** to write in your own words. Each section lists what to say, the numbers to use,
and the figure to include. Aim for 2–3 pages. All numbers are from Qwen3-4B-Instruct-2507 Q4_K_M,
llama.cpp b11954, RTX 3070 Ti Laptop (8 GB), 50 labelled items (25 Track A, 25 Track B), 3 repeats per setting.

---

## 2.1 Goal (1 paragraph)
- Phase 1 showed 100% of outputs *parse* as JSON. Phase 2 asks three harder questions:
  1. Do outputs match the **schema** (allowed values, field rules)?
  2. Are they **correct** (graded against gold labels)?
  3. How do **enforcement** and **temperature** change 1 and 2 — and at what latency cost?

## 2.2 Method (½ page)
- **Schemas:** Pydantic models `ProcessedNote` (Track A) and `NoteAnswer` (Track B); fixed vocabularies
  (6 note types, 20 tags); field rules (1–4 tags, ISO dates, summary ≤ 2 sentences, no extra keys).
- **Validation pipeline:** extract JSON → parse → Pydantic validate → context check (cited chunk ids exist).
  Four error types: empty / not_json / schema / context.
- **Retry:** exactly one, as a continued conversation: the model sees its own bad output plus the exact
  validation errors. Second failure → typed `FailedOutput`, never a crash.
- **Enforcement modes:** prompt_only · json_object (generic JSON grammar) · json_schema (Pydantic schema
  compiled to a GBNF grammar by llama-server; chunk ids bounded to 0–3).
- **Grader:** Track A field_score = mean(note_type, tag Jaccard, action-item F1, due-date accuracy,
  entity F1); Track B = all key facts present, correct abstention, hallucination, grounding.
  Failed outputs score 0. Retrieval miss (b017) expects abstention.
- **Temperature sweep:** 0 / 0.2 / 0.4 / 0.6 / 0.7, seeds 43–45 (one per repeat), modes interleaved;
  side test at 0.7 with top-k / top-p / min-p disabled.
- **Consistency metrics:** *identical* (same text across repeats) vs *agreement* (same note type + tag set +
  action count; same answerable flag + correctness).

## 2.3 Results — enforcement (temperature 0)
Table (from `results/summary/quality_phase1_phase2_t0/summary.md` and `phase2_enforcement/summary.md`):

| Setting | A valid | A quality | A latency (median) | B quality | B hallucination |
|---|---|---|---|---|---|
| Prompt only, no retry | 48% | 34% | ~2.9 s | 96% | 0% |
| Prompt only + retry | 80% | 54% | 4.9 s | 96% | 0% |
| Generic JSON + retry | 80% | 54% | 5.0 s | 96% | 0% |
| Schema + retry | 100% | 65% | 3.0 s | 96% | 0% |

Figure: `results/summary/phase2_enforcement/outcomes_stacked.png`

Points to make:
- **Parseable ≠ valid.** 100% parseable JSON, only 48% schema-valid on Track A. Errors were wrong *values*:
  note_type outside the enum (18), invented tags (18), summaries > 2 sentences (6), malformed dates (3).
- **Generic JSON mode changed nothing** — the model already writes valid JSON; the problem is the values.
- **Schema enforcement wins on validity, quality and latency**: avoiding retries is faster than repairing.
- **No content cost:** on notes already valid without enforcement, schema-mode output was identical
  (paired comparison). Its gain comes entirely from rescuing failures.
- The retry rescues ~62% of prompt-only failures but nearly doubles median latency.
- Track B (simpler schema) was 100% valid in every mode.

## 2.4 Results — content quality
- Track A ~65% field score even when 100% valid → the bottleneck is **judgment, not format**.
- Diagnostics: over-tagging (tag precision ~51%, recall ~88%); over-extracting entities (precision ~51%,
  recall ~99%); invented tasks on ~8% of notes (e.g. a005 journal entry); note_type ambiguity
  (journal / reference / todo).
- Track B: 96% correct, 100% correct abstention on the 5 unanswerable questions, 0% hallucination,
  100% grounded citations. Only miss: b019 date arithmetic ("14 days" instead of 48).

## 2.5 Results — temperature
Figures: `results/summary/phase2_temperature/agreement_vs_temperature.png` (main),
`first_try_valid_vs_temperature.png`, `quality_vs_temperature.png`.

| Temp | 0 | 0.2 | 0.4 | 0.6 | 0.7 |
|---|---|---|---|---|---|
| Schema: A first-try valid | 92% | 91% | 95% | 93% | 97% |
| Schema: A quality | 65% | 64% | 64% | 63% | 64% |
| Schema: A decision agreement | 100% | 64% | 40% | 16% | 16% |
| Prompt: A decision agreement | 100% | 56% | 44% | 28% | 24% |
| B decision agreement (both modes) | 100% | 100% | 100% | 100% | 100% |

Points to make:
- **Temperature costs consistency, not correctness.** Validity and mean quality are flat from 0 to 0.7;
  errors are systematic (the model "believes" admin is a note type), so randomness neither adds nor fixes many.
- **Tags drive the inconsistency:** tag-set agreement 100 → 68 → 40 → 24 → 24% (schema mode); note_type
  stays 88–100%, action-item count 88–96%.
- Track B decisions never change; only wording does (identical text 100% → 60%).
- **Filters off at 0.7 ≈ filters on** — the model's distribution is already peaked, so top-k/top-p/min-p
  have little tail to cut.
- **Recommendation:** temperature 0 for extraction (re-processing a note must give the same tags);
  Q&A tolerates 0.2–0.4.

## 2.6 Harness design notes (short, but interviewers love this)
Write 1–2 sentences each — *why* it was done:
- Validation separates syntax / schema / context errors → each is its own metric.
- Model call injected as `generate_fn` → retry logic unit-tested with a fake model (59 tests).
- Retry as a conversation with exact errors; fixed budget of one.
- Failure is a typed value, never an exception.
- Smoke tests before long runs caught two real problems: the grammar-cleaning bug (json_schema failed
  100%) and the fixed-seed flaw (temperature runs were one sample repeated).
- Seed = base + repeat: reproducible but genuinely different repeats.

## 2.7 Limitations
- One model and one quantization (Phase 3 and 4 extend this).
- Synthetic notes, single annotator; note_type and tag labels involve judgment → treat those scores as softer
  than due dates and Track B answers.
- Grader uses fuzzy matching (action items) and substring matching (key facts); title/summary not graded.
- 3 repeats per setting; laptop timing noise ±4–7% (Phase 1), so small latency differences are not meaningful.
- Track B's 5 unanswerable questions are a small sample for hallucination rates.
