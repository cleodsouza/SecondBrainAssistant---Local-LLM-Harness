"""Tests for harness/grade.py.  Run:  python -m pytest harness/tests -v"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from grade import entity_match, fact_present, grade_a, grade_b, similarity  # noqa: E402

GOLD_A = {
    "title": "Kestrel kickoff", "note_type": "meeting", "tags": ["work", "design"],
    "summary": "x", "entities": ["Kestrel", "Meera", "Dr. Neha Shah"],
    "action_items": [{"description": "Audit current onboarding flow", "due": "2026-07-10", "priority": "high"},
                     {"description": "Kabir: check DigiLocker feasibility", "due": None, "priority": "medium"}],
}


def pred(**over):
    base = {k: v for k, v in GOLD_A.items()}
    base.update(over)
    return base


def test_perfect_prediction_scores_1():
    g = grade_a(pred(), GOLD_A)
    assert g["field_score"] == 1.0 and not g["invented_tasks"]


def test_failed_output_scores_0():
    g = grade_a(None, GOLD_A)
    assert g["field_score"] == 0.0


def test_wrong_note_type():
    assert grade_a(pred(note_type="todo"), GOLD_A)["note_type"] == 0.0


def test_tags_jaccard_and_precision_recall():
    g = grade_a(pred(tags=["work", "design", "engineering", "productivity"]), GOLD_A)
    assert g["tags"] == pytest.approx(0.5)           # 2 shared / 4 in union
    assert g["tags_recall"] == 1.0 and g["tags_precision"] == 0.5   # over-tagging, nothing missed


def test_actions_fuzzy_match_and_due():
    acts = [{"description": "Audit the current onboarding flow", "due": "2026-07-11", "priority": "high"},
            {"description": "Kabir: check feasibility of DigiLocker", "due": None, "priority": "low"}]
    g = grade_a(pred(action_items=acts), GOLD_A)
    assert g["actions_f1"] == 1.0                    # both matched despite rewording
    assert g["due_acc"] == 0.5                       # one due date off by a day


def test_extra_action_lowers_f1():
    acts = GOLD_A["action_items"] + [{"description": "Book a flight to Pune", "due": None, "priority": "low"}]
    g = grade_a(pred(action_items=acts), GOLD_A)
    assert g["actions_f1"] == pytest.approx(0.8)     # P=2/3, R=1


def test_invented_tasks_flag():
    gold = dict(GOLD_A, action_items=[])
    g = grade_a(pred(action_items=[{"description": "Call mom", "due": None, "priority": "low"}]), gold)
    assert g["invented_tasks"] and g["actions_f1"] == 0.0
    g2 = grade_a(pred(action_items=[]), gold)
    assert not g2["invented_tasks"] and g2["actions_f1"] == 1.0 and g2["due_acc"] == 1.0


def test_entity_normalisation():
    assert entity_match("Neha Shah", "Dr. Neha Shah")
    assert entity_match("Airtel Xstream fiber", "Airtel Xstream")
    assert not entity_match("onboarding", "Kestrel")


def test_entities_overextraction_hits_precision_not_recall():
    g = grade_a(pred(entities=GOLD_A["entities"] + ["onboarding", "signup", "Android"]), GOLD_A)
    assert g["entities_recall"] == 1.0 and g["entities_precision"] == 0.5


def test_similarity_threshold_rejects_unrelated():
    assert similarity("Buy foam roller", "Return Amazon parcel") < 0.5


# ---------------------------------------------------------------- Track B
GOLD_B = {"answerable": True, "gold_in_topk": True, "key_facts": ["4,500|4500"], "gold_chunk_ids": [1]}
UNANS = {"answerable": False, "gold_in_topk": None, "key_facts": [], "gold_chunk_ids": []}


def test_fact_alternatives():
    assert fact_present("4,500|4500", "You paid Rs 4500 in advance.")
    assert not fact_present("4,500|4500", "You paid Rs 6,000.")


def test_correct_grounded_answer():
    g = grade_b({"answerable": True, "answer": "Rs 4,500 advance.", "source_chunk_ids": [1], "confidence": "high"}, GOLD_B)
    assert g["answer_ok"] and g["grounded"] and g["abstain_ok"] and g["qa_score"] == 1.0


def test_right_answer_wrong_citation_is_correct_but_ungrounded():
    g = grade_b({"answerable": True, "answer": "Rs 4,500.", "source_chunk_ids": [3], "confidence": "high"}, GOLD_B)
    assert g["answer_ok"] and g["grounded"] is False


def test_hallucination_on_unanswerable():
    g = grade_b({"answerable": True, "answer": "98201 55555", "source_chunk_ids": [0], "confidence": "low"}, UNANS)
    assert g["hallucinated"] and not g["abstain_ok"] and g["qa_score"] == 0.0


def test_abstaining_on_unanswerable_is_correct():
    g = grade_b({"answerable": False, "answer": None, "source_chunk_ids": [], "confidence": "low"}, UNANS)
    assert g["abstain_ok"] and g["answer_ok"] and not g["hallucinated"] and g["qa_score"] == 1.0


def test_retrieval_miss_expects_abstention():
    miss = dict(GOLD_B, gold_in_topk=False)
    g = grade_b({"answerable": False, "answer": None, "source_chunk_ids": [], "confidence": "low"}, miss)
    assert g["abstain_ok"] and g["qa_score"] == 1.0 and g["expected_answerable"] is False


def test_failed_output_track_b():
    assert grade_b(None, GOLD_B)["qa_score"] == 0.0
