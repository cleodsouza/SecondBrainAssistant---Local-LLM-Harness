"""
Phase 2.2 - structured generation with validation + one retry + typed failure.

    result = generate_structured(generate_fn, messages, ProcessedNote)
    result.status        -> "ok_first" | "ok_retry" | "failed"
    result.data          -> validated ProcessedNote / NoteAnswer, or None
    result.failure       -> FailedOutput (typed) when status == "failed", else None
    result.attempts      -> every attempt: raw text, error type/message, timing meta

Design notes (the "why", for the report's Harness design section)
  - The model call is injected as `generate_fn(messages) -> (text, meta)`. The wrapper never talks to
    llama-server directly, so it can be unit-tested with a fake model and reused with any backend.
  - The retry is a *conversation*, not a fresh prompt: the model sees its own bad output as an
    assistant turn, then a user turn with the exact validation errors. Models fix their own output far
    more reliably when they can see what they wrote.
  - Exactly ONE retry (configurable). More retries hide model weakness and multiply latency; the
    Phase 2 metric "retry success rate" is only meaningful with a fixed budget.
  - Failure is a value, not an exception. Downstream code always gets a typed object it can store,
    count and display - the app never crashes because the model misbehaved.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Optional, Type

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import ValidationResult, validate_output  # noqa: E402

GenerateFn = Callable[[list[dict]], tuple[str, dict]]
Status = Literal["ok_first", "ok_retry", "failed"]

RETRY_TEMPLATE = (
    "Your previous answer could not be accepted. Problems found:\n"
    "{errors}\n\n"
    "Return ONLY the corrected JSON object, with exactly the required keys. "
    "No explanation, no markdown."
)


class FailedOutput(BaseModel):
    """What callers receive instead of data when both attempts fail."""
    status: Literal["failed"] = "failed"
    error_type: str           # error type of the LAST attempt: empty / not_json / schema / context
    reason: str               # validation message of the last attempt
    raw_output: str           # last raw model text, kept for debugging and error analysis
    attempts: int


@dataclass
class Attempt:
    number: int               # 1 = first try, 2 = retry
    raw_text: str
    ok: bool
    error_type: Optional[str]
    error: Optional[str]
    meta: dict = field(default_factory=dict)   # timings / token counts from the backend


@dataclass
class StructuredResult:
    status: Status
    data: Optional[BaseModel]
    failure: Optional[FailedOutput]
    attempts: list[Attempt]

    @property
    def ok(self) -> bool:
        return self.status != "failed"

    @property
    def n_attempts(self) -> int:
        return len(self.attempts)


def build_retry_messages(messages: list[dict], bad_output: str, errors: str) -> list[dict]:
    """Original conversation + the model's bad answer + a correction request."""
    return messages + [
        {"role": "assistant", "content": bad_output},
        {"role": "user", "content": RETRY_TEMPLATE.format(errors=errors)},
    ]


def generate_structured(
    generate_fn: GenerateFn,
    messages: list[dict],
    schema: Type[BaseModel],
    n_chunks: Optional[int] = None,
    max_retries: int = 1,
) -> StructuredResult:
    attempts: list[Attempt] = []
    convo = messages
    result: Optional[ValidationResult] = None

    for number in range(1, max_retries + 2):          # 1 first try + max_retries retries
        try:
            text, meta = generate_fn(convo)
        except Exception as e:                        # backend failure (timeout, server down)
            text, meta = "", {"backend_error": repr(e)}
        result = validate_output(text, schema, n_chunks=n_chunks)
        if "backend_error" in meta and not result.ok:
            result.error = f"backend error: {meta['backend_error']}"
        attempts.append(Attempt(number, text, result.ok, result.error_type, result.error, meta))

        if result.ok:
            status: Status = "ok_first" if number == 1 else "ok_retry"
            return StructuredResult(status, result.data, None, attempts)

        if number <= max_retries:                     # prepare the retry conversation
            # Show the model its own output (empty output -> a placeholder so the turn isn't blank).
            convo = build_retry_messages(messages, text or "(empty response)", result.error or "")

    last = attempts[-1]
    failure = FailedOutput(error_type=last.error_type or "unknown", reason=last.error or "",
                           raw_output=last.raw_text, attempts=len(attempts))
    return StructuredResult("failed", None, failure, attempts)


# --------------------------------------------------------------------------- live demo
def _demo() -> None:
    """Try a few prompts against the running llama-server and print every attempt.

        python harness/structured.py               # a001, a008, b021
        python harness/structured.py a014 b017     # any item ids
        python harness/structured.py --temp 0.7 a008
    """
    import argparse
    import json

    from runner import LlamaServer, load_items, ROOT
    from validate import NoteAnswer, ProcessedNote

    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", default=["a001", "a008", "b021"])
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--server", default="http://127.0.0.1:8080")
    args = ap.parse_args()

    server = LlamaServer(args.server)
    server.wait_ready()
    params = {"temperature": args.temp, "seed": 42, "top_k": 40, "top_p": 0.95, "min_p": 0.05,
              "repeat_penalty": 1.0, "n_predict": 512}

    def generate(msgs: list[dict]) -> tuple[str, dict]:
        res = server.stream_completion(server.apply_template(msgs), params)
        t = res["final"].get("timings", {})
        return res["text"], {"latency_ms": res["latency_ms"], "predicted_n": t.get("predicted_n")}

    items = {it["item_id"]: it for it in load_items(ROOT / "second_brain_corpus" / "build", ["A", "B"])}
    for item_id in args.ids:
        it = items[item_id]
        schema = ProcessedNote if it["track"] == "A" else NoteAnswer
        n_chunks = 4 if it["track"] == "B" else None
        r = generate_structured(generate, it["messages"], schema, n_chunks=n_chunks)
        print(f"\n=== {item_id}  ->  {r.status}  ({r.n_attempts} attempt(s))")
        for a in r.attempts:
            flag = "OK " if a.ok else f"BAD ({a.error_type})"
            print(f"  attempt {a.number}: {flag}  {a.meta.get('latency_ms', 0):.0f} ms")
            if not a.ok:
                print("    " + (a.error or "").replace("\n", "\n    "))
        shown = r.data.model_dump(mode="json") if r.ok else r.failure.model_dump()
        print(json.dumps(shown, indent=2, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    _demo()
