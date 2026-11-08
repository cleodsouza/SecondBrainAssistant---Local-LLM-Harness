"""
Phase 2.4 - grader: is the content CORRECT, not just correctly shaped?

    python harness/grade.py --label enforcement results/raw/phase2_*.jsonl

Reads raw runner rows + the gold labels, scores every non-warm-up row, and writes
    results/graded/<run>.graded.jsonl          one graded row per input row (never edits raw files)
    results/summary/quality_<label>/summary.md  quality tables per (model, quant, enforcement, temperature)
    results/summary/quality_<label>/*.csv / *.png

Works on Phase 1 rows too (no `final_output` column): the raw text is validated on the fly.
A row whose output never became valid scores 0 on every metric ("failed counts as wrong").

TRACK A (note -> ProcessedNote), all metrics in [0, 1]
  note_type      exact match
  tags           Jaccard overlap with gold tags
  actions_f1     action items matched to gold by fuzzy description similarity (>= MATCH_THRESHOLD),
                 then F1 of the matching.  Both empty -> 1.0
  due_acc        of matched action items, share with exactly the right due date (null == null counts)
  entities_f1    F1 after normalising (case, titles like "Dr.", punctuation); "contains" counts as a match
  invented_tasks gold has NO action items but the model produced some (hallucination flag)
  field_score    mean of note_type, tags, actions_f1, due_acc, entities_f1  - the Track A headline number
  title / summary are free text and are NOT auto-graded (rubric or LLM judge later).

TRACK B (question + 4 chunks -> NoteAnswer)
  abstain_ok     model's answerable flag == expected; "expected" = gold answerable AND gold note retrieved
                 (if retrieval missed the gold note - b017 - the correct behaviour is to abstain)
  answer_ok      answerable item: every key fact present in the answer (alternatives "a|b").
                 unanswerable item: answer_ok == abstain_ok
  hallucinated   expected unanswerable, model answered anyway
  grounded       model cited at least one chunk that holds the gold note (answerable items it answered)
  qa_score       answer_ok - the Track B headline number
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import NoteAnswer, ProcessedNote, validate_output  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MATCH_THRESHOLD = 0.5
A_FIELDS = ["note_type", "tags", "actions_f1", "due_acc", "entities_f1"]
GROUP = ["model", "quant", "enforcement", "max_retries", "temperature", "track"]


# --------------------------------------------------------------------------- helpers
def norm(s: str) -> str:
    s = s.lower().replace("–", "-").replace("—", "-")
    s = re.sub(r"\b(dr|mr|mrs|ms)\.?\s+", "", s)
    s = re.sub(r"[^a-z0-9.+:/-]+", " ", s)
    return " ".join(s.split())


def f1(p: float, r: float) -> float:
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def similarity(a: str, b: str) -> float:
    """Fuzzy similarity of two task descriptions: max of character ratio and token overlap.
    Owner prefixes like "Kabir: ..." are kept - getting the owner right is part of the task."""
    a, b = norm(a), norm(b)
    ta, tb = set(a.split()), set(b.split())
    token = len(ta & tb) / max(1, min(len(ta), len(tb)))
    return max(SequenceMatcher(None, a, b).ratio(), token)


def match_items(pred: list, gold: list, key) -> list[tuple[int, int, float]]:
    """Greedy one-to-one matching by similarity, best pairs first."""
    pairs = sorted(((similarity(key(p), key(g)), i, j) for i, p in enumerate(pred) for j, g in enumerate(gold)),
                   reverse=True)
    used_p, used_g, out = set(), set(), []
    for s, i, j in pairs:
        if s < MATCH_THRESHOLD:
            break
        if i not in used_p and j not in used_g:
            used_p.add(i); used_g.add(j); out.append((i, j, s))
    return out


def entity_match(a: str, b: str) -> bool:
    a, b = norm(a), norm(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def set_prf(pred: list[str], gold: list[str], same) -> tuple[float, float, float]:
    """Precision (share of predicted items that are right), recall (share of gold found), F1."""
    if not pred and not gold:
        return 1.0, 1.0, 1.0
    if not pred or not gold:
        return (0.0 if pred else 1.0), (0.0 if gold else 1.0), 0.0
    p = sum(any(same(x, g) for g in gold) for x in pred) / len(pred)
    r = sum(any(same(x, g) for x in pred) for g in gold) / len(gold)
    return p, r, f1(p, r)


def fact_present(fact: str, answer: str) -> bool:
    text = norm(answer)
    return any(norm(alt) in text for alt in fact.split("|"))


# --------------------------------------------------------------------------- graders
def grade_a(pred: dict | None, gold: dict) -> dict:
    gold_actions = gold["action_items"]
    if pred is None:
        return {**{k: 0.0 for k in A_FIELDS}, "field_score": 0.0, "invented_tasks": False,
                "tags_precision": 0.0, "tags_recall": 0.0, "entities_precision": 0.0, "entities_recall": 0.0,
                "n_pred_actions": None, "n_gold_actions": len(gold_actions)}
    acts = pred.get("action_items", [])
    matches = match_items(acts, gold_actions, key=lambda t: t["description"])
    if not acts and not gold_actions:
        actions_f1 = 1.0
    else:
        actions_f1 = f1(len(matches) / len(acts) if acts else 0.0,
                        len(matches) / len(gold_actions) if gold_actions else 0.0)
    if matches:
        due_acc = sum(acts[i].get("due") == gold_actions[j].get("due") for i, j, _ in matches) / len(matches)
    else:
        due_acc = 1.0 if not gold_actions and not acts else 0.0
    gt, pt = set(gold["tags"]), set(pred.get("tags", []))
    tag_p, tag_r, _ = set_prf(list(pt), list(gt), lambda a, b: a == b)
    ent_p, ent_r, ent_f1 = set_prf(pred.get("entities", []), gold["entities"], entity_match)
    scores = {
        "note_type": float(pred.get("note_type") == gold["note_type"]),
        "tags": len(gt & pt) / len(gt | pt) if gt | pt else 1.0,
        "actions_f1": actions_f1,
        "due_acc": due_acc,
        "entities_f1": ent_f1,
    }
    return {**scores, "field_score": sum(scores.values()) / len(scores),
            "invented_tasks": (not gold_actions) and bool(acts),
            "tags_precision": tag_p, "tags_recall": tag_r,
            "entities_precision": ent_p, "entities_recall": ent_r,
            "n_pred_actions": len(acts), "n_gold_actions": len(gold_actions)}


def grade_b(pred: dict | None, gold: dict) -> dict:
    expected = bool(gold["answerable"] and gold.get("gold_in_topk"))
    if pred is None:
        return {"abstain_ok": False, "answer_ok": False, "hallucinated": False, "grounded": None,
                "qa_score": 0.0, "expected_answerable": expected}
    said = bool(pred.get("answerable"))
    abstain_ok = said == expected
    if expected:
        answer_ok = said and all(fact_present(f, pred.get("answer") or "") for f in gold["key_facts"])
        cited = set(pred.get("source_chunk_ids") or [])
        grounded = bool(cited & set(gold.get("gold_chunk_ids") or [])) if said else None
    else:
        answer_ok, grounded = abstain_ok, None
    return {"abstain_ok": abstain_ok, "answer_ok": answer_ok, "hallucinated": (not expected) and said,
            "grounded": grounded, "qa_score": float(answer_ok), "expected_answerable": expected}


# --------------------------------------------------------------------------- pipeline
def load_gold(build: Path) -> tuple[dict, dict, dict]:
    read = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]  # noqa: E731
    gold_a = {a["id"]: a["expected"] for a in read(build / "track_a.jsonl")}
    meta_a = {a["id"]: a for a in read(build / "track_a.jsonl")}
    notes = {n["id"]: n for n in read(build / "notes.jsonl")}
    for a in meta_a.values():
        a["edge_case"] = notes[a["note_id"]].get("edge_case")
    gold_b = {b["id"]: b for b in read(build / "track_b_frozen.jsonl")}
    return gold_a, meta_a, gold_b


def final_output_of(row: dict) -> dict | None:
    """Phase 2+ rows carry the validated output; Phase 1 rows only have raw text -> validate now."""
    if "status" in row:
        return row.get("final_output")
    schema = ProcessedNote if row["track"] == "A" else NoteAnswer
    r = validate_output(row.get("output_text") or "", schema, n_chunks=4 if row["track"] == "B" else None)
    return r.data.model_dump(mode="json") if r.ok else None


def grade_rows(rows: list[dict], gold_a, meta_a, gold_b) -> list[dict]:
    out = []
    for row in rows:
        if row.get("is_warmup"):
            continue
        pred = final_output_of(row)
        base = {k: row.get(k) for k in ("run_id", "model", "quant", "enforcement", "temperature", "seed",
                                        "track", "item_id", "repeat", "status")}
        base["enforcement"] = base["enforcement"] or "prompt_only"
        base["max_retries"] = row.get("max_retries") or 0        # Phase 1 rows: no retry
        base["sampling_filters"] = row.get("sampling_filters") or "on"
        base["total_latency_ms"] = row.get("total_latency_ms") or row.get("latency_ms")
        base["first_error_type"] = row.get("first_error_type")
        base["final_json"] = json.dumps(pred, sort_keys=True) if pred is not None else None
        base["valid"] = pred is not None
        if row["track"] == "A":
            g = grade_a(pred, gold_a[row["item_id"]])
            base.update(difficulty=meta_a[row["item_id"]]["difficulty"],
                        edge_case=meta_a[row["item_id"]]["edge_case"])
        else:
            gb = gold_b[row["item_id"]]
            g = grade_b(pred, gb)
            base.update(difficulty=gb["difficulty"], question_type=gb["question_type"])
        out.append({**base, **g})
    return out


def summarise(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    a = df[df.track == "A"]
    b = df[df.track == "B"]
    ta = a.groupby(GROUP, dropna=False).agg(
        n=("item_id", "size"), valid=("valid", "mean"), field_score=("field_score", "mean"),
        note_type=("note_type", "mean"), tags=("tags", "mean"), actions_f1=("actions_f1", "mean"),
        due_acc=("due_acc", "mean"), entities_f1=("entities_f1", "mean"),
        invented_tasks=("invented_tasks", "mean"),
        tags_precision=("tags_precision", "mean"), tags_recall=("tags_recall", "mean"),
        entities_precision=("entities_precision", "mean"), entities_recall=("entities_recall", "mean"),
        n_pred_actions=("n_pred_actions", "mean"), n_gold_actions=("n_gold_actions", "mean")).reset_index()
    # Quality of VALID outputs only: separates "fewer failures" from "better content".
    valid_only = a[a["valid"]].groupby(GROUP, dropna=False)["field_score"].mean().rename("field_score_valid_only")
    ta = ta.merge(valid_only.reset_index(), on=GROUP, how="left")
    rows = []
    for key, g in b.groupby(GROUP, dropna=False):
        exp = g["expected_answerable"].astype(bool)
        grounded = g["grounded"].dropna()
        rows.append({**dict(zip(GROUP, key)), "n": len(g), "valid": g["valid"].mean(),
                     "qa_score": g["qa_score"].mean(), "abstain_ok": g["abstain_ok"].astype(bool).mean(),
                     "answered_correctly": g.loc[exp, "answer_ok"].astype(bool).mean(),
                     "hallucination_rate": g.loc[~exp, "hallucinated"].astype(bool).mean(),
                     "grounded": grounded.astype(bool).mean() if len(grounded) else float("nan")})
    return ta, pd.DataFrame(rows)


def md_table(t: pd.DataFrame, cols: list[str]) -> str:
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in t.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float) and c not in ("temperature",):
                cells.append("-" if pd.isna(v) else f"{v:.0%}" if c != "n" else f"{v:.0f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--label", default="run")
    ap.add_argument("--corpus", default=str(ROOT / "second_brain_corpus" / "build"))
    args = ap.parse_args()

    gold_a, meta_a, gold_b = load_gold(Path(args.corpus))
    graded_dir = ROOT / "results" / "graded"
    graded_dir.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for p in args.paths:
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        g = grade_rows(rows, gold_a, meta_a, gold_b)
        with open(graded_dir / (Path(p).stem + ".graded.jsonl"), "w", encoding="utf-8") as f:
            for r in g:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        all_rows += g

    df = pd.DataFrame(all_rows)
    df["temperature"] = df["temperature"].astype(float)
    ta, tb = summarise(df)
    out = ROOT / "results" / "summary" / f"quality_{args.label}"
    out.mkdir(parents=True, exist_ok=True)
    ta.to_csv(out / "track_a_quality.csv", index=False)
    tb.to_csv(out / "track_b_quality.csv", index=False)

    # Per-item view: which items are hard for everyone? (mean field_score / qa_score across all rows)
    per_item = (df.assign(score=df["field_score"].fillna(df["qa_score"]))
                  .groupby(["track", "item_id"])["score"].mean().sort_values().round(2))
    per_item.to_csv(out / "per_item_scores.csv")
    by_diff = df.assign(score=df["field_score"].fillna(df["qa_score"])) \
                .groupby(["track", "difficulty"])["score"].mean().round(2)

    md = [f"# Quality summary - {args.label}", "",
          f"Rows graded: {len(df)} (warm-up excluded). Failed outputs score 0.", "",
          "## Track A - note processing (field accuracy)", "",
          md_table(ta, GROUP[2:5] + ["n", "valid", "field_score", "field_score_valid_only", "note_type", "tags",
                                     "actions_f1", "due_acc", "entities_f1", "invented_tasks"]), "",
          "Diagnostics - precision = share of the model's items that are right, recall = share of gold found:", "",
          md_table(ta, GROUP[2:5] + ["tags_precision", "tags_recall", "entities_precision", "entities_recall"]), "",
          "## Track B - ask my notes", "",
          md_table(tb, GROUP[2:5] + ["n", "valid", "qa_score", "answered_correctly", "abstain_ok",
                                     "hallucination_rate", "grounded"]), "",
          "## Score by difficulty (all settings pooled)", "", "```", by_diff.to_string(), "```", "",
          "## Hardest items (all settings pooled)", "", "```", per_item.head(12).to_string(), "```", ""]
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\ngraded rows -> {graded_dir}\nsummary -> {out}")


if __name__ == "__main__":
    main()
