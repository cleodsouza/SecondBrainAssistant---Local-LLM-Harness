"""Tests for harness/validate.py.  Run:  python -m pytest harness/tests/test_validate.py -v"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from validate import NoteAnswer, ProcessedNote, extract_json, validate_output  # noqa: E402

GOOD_NOTE = {
    "title": "Kestrel kickoff",
    "note_type": "meeting",
    "tags": ["work", "design"],
    "summary": "Kickoff for the onboarding redesign. Launch target is Oct 15.",
    "action_items": [{"description": "Audit current flow", "due": "2026-07-10", "priority": "high"}],
    "entities": ["Kestrel", "Meera"],
}
GOOD_ANSWER = {"answerable": True, "answer": "Mulshi, 13-15 Nov.", "source_chunk_ids": [1], "confidence": "high"}
NO_ANSWER = {"answerable": False, "answer": None, "source_chunk_ids": [], "confidence": "low"}


# ---------------------------------------------------------------- extract_json
def test_extract_plain():
    s = json.dumps(GOOD_NOTE)
    assert json.loads(extract_json(s)) == GOOD_NOTE


def test_extract_strips_whitespace():
    assert json.loads(extract_json("\n\n  " + json.dumps(GOOD_ANSWER) + "  \n")) == GOOD_ANSWER


def test_extract_code_fence_with_lang():
    s = "```json\n" + json.dumps(GOOD_ANSWER, indent=2) + "\n```"
    assert json.loads(extract_json(s)) == GOOD_ANSWER


def test_extract_code_fence_without_lang():
    s = "```\n" + json.dumps(GOOD_ANSWER) + "\n```"
    assert json.loads(extract_json(s)) == GOOD_ANSWER


def test_extract_prose_around():
    s = "Here is the JSON you asked for:\n" + json.dumps(GOOD_NOTE) + "\nLet me know if you need anything else!"
    assert json.loads(extract_json(s)) == GOOD_NOTE


def test_extract_ignores_braces_inside_strings():
    obj = dict(GOOD_NOTE, summary="Uses a {placeholder} in text. It ends here.")
    s = "Sure: " + json.dumps(obj) + " {not json}"
    assert json.loads(extract_json(s)) == obj


def test_extract_no_brace_returns_text():
    assert extract_json("  no json here  ") == "no json here"


# ---------------------------------------------------------------- validate_output: success
def test_valid_note():
    r = validate_output(json.dumps(GOOD_NOTE), ProcessedNote)
    assert r.ok and r.error is None and r.error_type is None
    assert isinstance(r.data, ProcessedNote) and r.data.tags == ["work", "design"]


def test_valid_note_in_fence():
    r = validate_output("```json\n" + json.dumps(GOOD_NOTE) + "\n```", ProcessedNote)
    assert r.ok


def test_valid_unanswerable():
    r = validate_output(json.dumps(NO_ANSWER), NoteAnswer, n_chunks=4)
    assert r.ok and r.data.answerable is False


# ---------------------------------------------------------------- validate_output: failures
@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_empty(text):
    r = validate_output(text, ProcessedNote)
    assert not r.ok and r.error_type == "empty" and r.data is None


def test_not_json_trailing_comma():
    r = validate_output('{"answerable": true, "answer": "x", "source_chunk_ids": [0], "confidence": "high",}', NoteAnswer)
    assert not r.ok and r.error_type == "not_json" and r.error


def test_not_json_truncated():
    r = validate_output(json.dumps(GOOD_NOTE)[:-20], ProcessedNote)   # cut off mid-object (hit max tokens)
    assert not r.ok and r.error_type == "not_json"


def test_schema_tag_not_in_vocab():
    r = validate_output(json.dumps(dict(GOOD_NOTE, tags=["work", "travelling"])), ProcessedNote)
    assert not r.ok and r.error_type == "schema"
    assert "tags" in r.error and "travelling" in r.error      # message names the field AND the bad value


def test_schema_extra_key():
    r = validate_output(json.dumps(dict(GOOD_NOTE, mood="happy")), ProcessedNote)
    assert not r.ok and r.error_type == "schema" and "mood" in r.error


def test_schema_missing_key():
    bad = {k: v for k, v in GOOD_NOTE.items() if k != "note_type"}
    r = validate_output(json.dumps(bad), ProcessedNote)
    assert not r.ok and r.error_type == "schema" and "note_type" in r.error


def test_schema_summary_too_long():
    r = validate_output(json.dumps(dict(GOOD_NOTE, summary="One. Two. Three.")), ProcessedNote)
    assert not r.ok and r.error_type == "schema" and "summary" in r.error


def test_schema_bad_date():
    item = dict(GOOD_NOTE["action_items"][0], due="next Friday")
    r = validate_output(json.dumps(dict(GOOD_NOTE, action_items=[item])), ProcessedNote)
    assert not r.ok and r.error_type == "schema" and "due" in r.error


def test_schema_answer_given_when_unanswerable():
    r = validate_output(json.dumps(dict(NO_ANSWER, answer="Probably Rs 800")), NoteAnswer, n_chunks=4)
    assert not r.ok and r.error_type == "schema"


def test_context_chunk_out_of_range():
    r = validate_output(json.dumps(dict(GOOD_ANSWER, source_chunk_ids=[1, 6])), NoteAnswer, n_chunks=4)
    assert not r.ok and r.error_type == "context" and "6" in r.error


def test_context_check_skipped_without_n_chunks():
    r = validate_output(json.dumps(dict(GOOD_ANSWER, source_chunk_ids=[6])), NoteAnswer)
    assert r.ok


def test_error_message_is_compact():
    bad = dict(GOOD_NOTE, note_type="memo", tags=["x", "y"], summary="a. b. c.", mood=1)
    r = validate_output(json.dumps(bad), ProcessedNote)
    assert not r.ok and r.error.count("\n") < 10 and len(r.error) < 1500


def test_never_raises_on_garbage():
    for junk in ["{", "}", "[]", "null", "42", '"string"', "{{{{", "```json\n```"]:
        r = validate_output(junk, ProcessedNote)
        assert r.ok is False and r.error_type in {"empty", "not_json", "schema"}


def test_cleaned_text_recorded():
    r = validate_output("Sure!\n" + json.dumps(GOOD_ANSWER), NoteAnswer)
    assert r.cleaned_text.startswith("{") and r.cleaned_text.endswith("}")
