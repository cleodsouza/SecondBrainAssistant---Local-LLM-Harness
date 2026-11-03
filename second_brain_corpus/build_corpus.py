"""
Validate the hand-written YAML corpus and export benchmark-ready JSONL.

    python build_corpus.py

Reads   data/notes.yaml, data/track_a.yaml, data/track_b.yaml
Writes  build/notes.jsonl, build/track_a.jsonl, build/track_b.jsonl
Exits non-zero on any schema error or broken cross-reference, so it is safe to run in CI.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from pydantic import ValidationError

from schemas import Note, TrackAItem, TrackBItem

ROOT = Path(__file__).parent
DATA, BUILD = ROOT / "data", ROOT / "build"


def load(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate(raw: list[dict], model, label: str) -> list:
    out, errors = [], 0
    for item in raw:
        try:
            out.append(model.model_validate(item))
        except ValidationError as e:
            errors += 1
            print(f"[{label}] {item.get('id', '?')}: {e}", file=sys.stderr)
    if errors:
        sys.exit(f"{errors} {label} item(s) failed validation")
    ids = [x.id for x in out]
    dupes = [i for i, c in Counter(ids).items() if c > 1]
    if dupes:
        sys.exit(f"duplicate {label} ids: {dupes}")
    return out


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower())


def main() -> None:
    notes = validate(load("notes.yaml"), Note, "note")
    track_a = validate(load("track_a.yaml"), TrackAItem, "track_a")
    track_b = validate(load("track_b.yaml"), TrackBItem, "track_b")
    by_id = {n.id: n for n in notes}

    problems: list[str] = []
    warnings: list[str] = []

    # --- Track A cross-checks ---
    seen_notes = set()
    for a in track_a:
        note = by_id.get(a.note_id)
        if note is None:
            problems.append(f"{a.id}: unknown note_id {a.note_id}")
            continue
        if a.note_id in seen_notes:
            problems.append(f"{a.id}: note {a.note_id} labelled twice")
        seen_notes.add(a.note_id)
        for t in a.expected.action_items:
            if t.due and t.due < note.created:
                problems.append(f"{a.id}: due {t.due} is before note date {note.created}")
        body = norm(note.body)
        for ent in a.expected.entities:
            # Loose check: every entity should be grounded in the note text (first word is enough,
            # so "Dr. Neha Shah" or "Airtel Xstream" pass if their key token appears).
            key = norm(ent).split()
            if key and not any(tok in body.split() for tok in key if len(tok) > 2):
                warnings.append(f"{a.id}: entity '{ent}' not found in {a.note_id}")

    # --- Track B cross-checks ---
    for b in track_b:
        for nid in b.gold_note_ids:
            if nid not in by_id:
                problems.append(f"{b.id}: unknown gold note {nid}")
        if b.answerable:
            gold_text = norm(" ".join(by_id[n].body for n in b.gold_note_ids if n in by_id))
            for fact in b.key_facts:
                alts = [norm(x).strip() for x in fact.split("|")]
                # temporal / arithmetic facts (e.g. "48 days", "1.2 lakh") are derived, not quoted
                if b.question_type not in ("temporal", "multi_note") and not any(a in gold_text for a in alts):
                    warnings.append(f"{b.id}: key fact '{fact}' not literally in gold notes")

    if problems:
        print("\n".join(problems), file=sys.stderr)
        sys.exit(f"{len(problems)} cross-reference problem(s)")

    # --- Export ---
    BUILD.mkdir(exist_ok=True)
    for name, items in (("notes", notes), ("track_a", track_a), ("track_b", track_b)):
        with open(BUILD / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for it in items:
                f.write(it.model_dump_json() + "\n")

    # --- Stats ---
    words = [len(n.body.split()) for n in notes]
    print(f"notes:   {len(notes)}  (words min/median/max = {min(words)}/{sorted(words)[len(words)//2]}/{max(words)})")
    print(f"         edge cases: {dict(Counter(n.edge_case for n in notes if n.edge_case))}")
    print(f"track A: {len(track_a)}  types={dict(Counter(a.expected.note_type for a in track_a))}")
    print(f"         difficulty={dict(Counter(a.difficulty for a in track_a))}  "
          f"action_items={sum(len(a.expected.action_items) for a in track_a)}  "
          f"with_due={sum(1 for a in track_a for t in a.expected.action_items if t.due)}")
    print(f"track B: {len(track_b)}  answerable={sum(b.answerable for b in track_b)}  "
          f"unanswerable={sum(not b.answerable for b in track_b)}")
    print(f"         types={dict(Counter(b.question_type for b in track_b))}")
    print(f"         difficulty={dict(Counter(b.difficulty for b in track_b))}")
    for w in warnings:
        print(f"WARN {w}")
    print(f"OK - wrote {BUILD}/notes.jsonl, track_a.jsonl, track_b.jsonl")


if __name__ == "__main__":
    main()
