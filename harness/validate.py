"""
Phase 2.1 - validation layer.

Turns raw model text into a validated Pydantic object, or a precise, typed error.
The error message matters: in step 2.2 it is sent back to the model as feedback for the one retry,
so it must say exactly what was wrong ("tags.0: 'travelling' is not one of ...").

Run the tests from D:\\SLM Project:
    python -m pytest harness/tests/test_validate.py -v

Concepts this file teaches
  - LLM output is untrusted input: parse defensively, never eval, never assume shape.
  - Separate *syntax* errors (not JSON) from *schema* errors (JSON, wrong shape) from *context* errors
    (valid shape, but refers to something that doesn't exist - e.g. chunk 7 when only 4 were given).
    Each needs different feedback and is a different metric in the report.
  - Pydantic v2: model_validate_json() vs model_validate(), ValidationError.errors() structure.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Type

from pydantic import BaseModel, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "second_brain_corpus"))
from schemas import NoteAnswer, ProcessedNote  # noqa: E402,F401  (re-exported for callers)

MAX_ERROR_LINES = 10
ErrorType = Literal["empty", "not_json", "schema", "context"]


@dataclass
class ValidationResult:
    ok: bool
    data: Optional[BaseModel]       # the validated object when ok, else None
    error_type: Optional[ErrorType]  # None when ok
    error: Optional[str]            # human/model-readable message when not ok, else None
    cleaned_text: str               # the text that was actually parsed (after extract_json)


def extract_json(text: str) -> str:
    """Return the JSON object substring from raw model output.

    Must handle:
      - surrounding whitespace
      - markdown code fences: ```json ... ```  or  ``` ... ```
      - short prose before/after the object ("Here is the JSON: {...} Hope this helps")
    Strategy hint: find the first '{' and its *matching* closing '}' (count braces, and ignore braces
    inside JSON strings). If there is no '{', return the stripped text unchanged.
    """
    t = text.strip()
    # Remove markdown fences: ```json ... ```  or  ``` ... ```
    t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t).strip()

    start = t.find("{")
    if start == -1:
        return t

    # Walk forward counting braces; braces inside JSON strings don't count.
    depth, in_string, escaped = 0, False, False
    for i in range(start, len(t)):
        ch = t[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return t[start:i + 1]
    return t[start:]          # never closed (e.g. truncated output) -> json.loads will report it


def format_errors(exc) -> str:
    """Turn a pydantic.ValidationError into a compact message, one line per error, e.g.
        tags.0: Input should be 'work', 'design', ... [got 'travelling']
        summary: Value error, summary must be at most 2 sentences
    Use exc.errors(): each item has 'loc' (tuple), 'msg' (str) and 'input'.
    Kept short on purpose - this text is sent back to the model in the retry.
    """
    lines = []
    for err in exc.errors()[:MAX_ERROR_LINES]:
        loc = ".".join(str(part) for part in err["loc"]) or "(object)"
        line = f"{loc}: {err['msg']}"
        bad = err.get("input")
        if not isinstance(bad, (dict, list)):          # show scalar bad values, not whole objects
            line += f" [got {bad!r}]"
        lines.append(line)
    extra = len(exc.errors()) - len(lines)
    if extra > 0:
        lines.append(f"... and {extra} more error(s)")
    return "\n".join(lines)


def validate_output(text: str, schema: Type[BaseModel], n_chunks: Optional[int] = None) -> ValidationResult:
    """Validate raw model output against `schema` (ProcessedNote or NoteAnswer).

    Order of checks:
      1. empty / whitespace-only            -> error_type "empty"
      2. extract_json, then JSON parse fails -> error_type "not_json"   (include the parser's message)
      3. Pydantic validation fails           -> error_type "schema"     (use format_errors)
      4. NoteAnswer only, when n_chunks is given: call data.check_chunk_ids(n_chunks);
         a ValueError there                  -> error_type "context"
    Never raises - every failure becomes a ValidationResult with ok=False.
    """
    # 1. empty
    if not text or not text.strip():
        return ValidationResult(False, None, "empty", "empty output", "")

    cleaned = extract_json(text)

    # 2. syntax - is it JSON at all?
    try:
        json.loads(cleaned)
    except json.JSONDecodeError as e:
        return ValidationResult(False, None, "not_json", f"invalid JSON: {e}", cleaned)

    # 3. schema - is it the right shape?
    try:
        data = schema.model_validate_json(cleaned)
    except ValidationError as e:
        return ValidationResult(False, None, "schema", format_errors(e), cleaned)

    # 4. context - does it only cite chunks that were actually given?
    if n_chunks is not None and isinstance(data, NoteAnswer):
        try:
            data.check_chunk_ids(n_chunks)
        except ValueError as e:
            return ValidationResult(False, None, "context", str(e), cleaned)

    return ValidationResult(True, data, None, None, cleaned)
