"""Tests for harness/structured.py, using a fake model.  Run:  python -m pytest harness/tests -v"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from structured import RETRY_TEMPLATE, generate_structured  # noqa: E402
from validate import NoteAnswer, ProcessedNote  # noqa: E402

GOOD = json.dumps({"answerable": True, "answer": "Mulshi.", "source_chunk_ids": [0], "confidence": "high"})
GOOD_NOTE = json.dumps({"title": "Errands", "note_type": "todo", "tags": ["admin"],
                        "summary": "A short errand list.", "action_items": [], "entities": []})
MSGS = [{"role": "system", "content": "sys"}, {"role": "user", "content": "question"}]


class FakeModel:
    """Returns scripted outputs in order and records every conversation it was sent."""
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out, {"latency_ms": 10.0}


def test_ok_first_try_makes_one_call():
    fake = FakeModel(GOOD)
    r = generate_structured(fake, MSGS, NoteAnswer, n_chunks=4)
    assert r.status == "ok_first" and r.ok and r.n_attempts == 1 and len(fake.calls) == 1
    assert isinstance(r.data, NoteAnswer) and r.failure is None


def test_retry_fixes_it():
    fake = FakeModel("Sure! {not valid", GOOD)
    r = generate_structured(fake, MSGS, NoteAnswer, n_chunks=4)
    assert r.status == "ok_retry" and r.n_attempts == 2
    assert r.attempts[0].ok is False and r.attempts[0].error_type == "not_json"
    assert r.attempts[1].ok is True


def test_retry_conversation_contains_bad_output_and_errors():
    bad = json.dumps({"answerable": True, "answer": "x", "source_chunk_ids": [9], "confidence": "high"})
    fake = FakeModel(bad, GOOD)
    generate_structured(fake, MSGS, NoteAnswer, n_chunks=4)
    retry_convo = fake.calls[1]
    assert retry_convo[:2] == MSGS                                   # original turns kept
    assert retry_convo[2] == {"role": "assistant", "content": bad}   # model sees its own output
    assert retry_convo[3]["role"] == "user" and "9" in retry_convo[3]["content"]  # and the exact error
    assert retry_convo[3]["content"].startswith(RETRY_TEMPLATE.split("{")[0])


def test_original_messages_not_mutated():
    msgs = [dict(m) for m in MSGS]
    generate_structured(FakeModel("bad", GOOD), msgs, NoteAnswer)
    assert msgs == MSGS


def test_fails_gracefully_after_one_retry():
    fake = FakeModel("nope", '{"title": "x"}')
    r = generate_structured(fake, MSGS, ProcessedNote)
    assert r.status == "failed" and not r.ok and r.data is None and len(fake.calls) == 2
    f = r.failure
    assert f.status == "failed" and f.attempts == 2 and f.error_type == "schema"
    assert f.raw_output == '{"title": "x"}' and "note_type" in f.reason


def test_max_retries_zero_means_single_attempt():
    fake = FakeModel("nope")
    r = generate_structured(fake, MSGS, ProcessedNote, max_retries=0)
    assert r.status == "failed" and len(fake.calls) == 1


def test_empty_output_gets_placeholder_in_retry():
    fake = FakeModel("", GOOD_NOTE)
    r = generate_structured(fake, MSGS, ProcessedNote)
    assert r.status == "ok_retry"
    assert fake.calls[1][2]["content"] == "(empty response)"


def test_backend_exception_becomes_failed_attempt_not_crash():
    fake = FakeModel(TimeoutError("server timed out"), GOOD)
    r = generate_structured(fake, MSGS, NoteAnswer)
    assert r.status == "ok_retry"
    assert "backend error" in r.attempts[0].error and "timed out" in r.attempts[0].error


def test_failure_object_is_serialisable():
    r = generate_structured(FakeModel("a", "b"), MSGS, NoteAnswer)
    dumped = r.failure.model_dump_json()
    assert json.loads(dumped)["status"] == "failed"
