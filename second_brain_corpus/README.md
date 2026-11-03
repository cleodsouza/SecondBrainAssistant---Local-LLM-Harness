# Second Brain benchmark corpus

A synthetic personal-knowledge base plus two labelled prompt sets for benchmarking local SLMs
(Phases 1-4). Retrieval is plumbing: it runs once and the contexts are frozen.

## Contents

| Path | What it is |
|---|---|
| `schemas.py` | Pydantic models: **output** schemas the SLM must produce (`ProcessedNote`, `NoteAnswer`) and **corpus** schemas (`Note`, `TrackAItem`, `TrackBItem`). Fixed tag + note-type vocabularies. |
| `data/notes.yaml` | 60 notes from one fictional person (Aarav, product designer in Mumbai), Jul-Oct 2026, with recurring threads so questions can span notes. |
| `data/track_a.yaml` | 25 note-processing prompts with gold `ProcessedNote` labels + the labelling rules. |
| `data/track_b.yaml` | 25 ask-my-notes questions: 20 answerable (with gold notes + key facts), 5 unanswerable. |
| `build_corpus.py` | Validates everything against the schemas, cross-checks references, exports JSONL to `build/`. |
| `freeze_contexts.py` | Embeds notes into Chroma once, retrieves top-4 per question, writes `build/track_b_frozen.jsonl` + `build/retrieval_config.json` (incl. recall@4). |

## Run it

```bash
pip install pydantic pyyaml chromadb sentence-transformers
python build_corpus.py        # validate + export  -> build/notes.jsonl, track_a.jsonl, track_b.jsonl
python freeze_contexts.py     # retrieve once      -> build/track_b_frozen.jsonl, retrieval_config.json
```

`build_corpus.py` exits non-zero on any schema error, so edit the YAML freely and re-run it.
It prints one expected warning (`Amazon` in a008 is inferred from "amzn" on purpose).

## Corpus design

**Threads:** Kestrel (onboarding redesign at work) - Mulshi trip - half-marathon + knee injury -
sister's wedding - reading - `streak` Rust CLI - finance - landlord/home - career - guitar.

**Edge cases (tagged `edge_case` on the note):** Hinglish (2), shorthand with typos (1), no action items (4),
duplicate idea (1, n005 vs n022), long note (1, ~300 words), vague dates (2).

**Built-in distractors for Track B:** the knee note mentions a 14 km run vs the 16 km longest run; the
Nashik note says "book train tickets" but never confirms a booking; Lonavala and Mulshi both appear.

## Grading guide

**Track A (`ProcessedNote`):**

| Field | Metric |
|---|---|
| `note_type` | exact match (accuracy) |
| `tags` | Jaccard / F1 against gold |
| `action_items` | count match + F1 on fuzzy-matched descriptions; `due` exact match on matched items |
| `entities` | F1 after lowercasing + fuzzy match |
| `title`, `summary` | 1-5 rubric (you or a fixed-rubric LLM judge) |

Date rules for the system prompt: resolve relative dates against the note's `created` date; vague ranges
("this week", "in November", "sometime") stay `null`; "end of November" -> 2026-11-30.

**Track B (`NoteAnswer`):**

| Metric | How |
|---|---|
| Answer correctness | all `key_facts` present (case-insensitive; `a|b` = alternatives) |
| Grounding | cited `source_chunk_ids` overlap `gold_chunk_ids` |
| Abstention | `answerable` matches gold - false-answer rate on the 5 unanswerable items = hallucination rate |
| Retrieval-aware error split | report errors separately for `gold_in_topk = true` vs `false` |

## Counts

- Notes: 60 (16-296 words, median 34)
- Track A: 25 items - 42 action items (16 with due dates) - difficulty easy 5 / medium 13 / hard 7
- Track B: 25 items - lookup 15, temporal 2, multi-note 2, aggregation 1, unanswerable 5
