"""
Phase 2.3 - output enforcement modes.

How strongly do we force the model's output into shape?

  prompt_only  - the system prompt describes the JSON; decoding is unconstrained.
                 The model *can* emit anything (prose, fences, wrong keys).
  json_object  - llama-server constrains decoding to ANY syntactically valid JSON object
                 (generic grammar). Guarantees parseable JSON, says nothing about keys or values.
  json_schema  - llama-server converts our Pydantic schema into a GBNF grammar, so at every step
                 only tokens that keep the output schema-valid can be sampled: allowed keys only,
                 enum values only (tags, note_type), ISO dates, 1-4 tags, chunk ids 0..k-1.

What a grammar CANNOT enforce (still checked by validate.py, so still visible in the results):
  - summary <= 2 sentences            (a semantic rule in a Pydantic validator)
  - answerable=false  =>  answer=null (a cross-field rule in a model_validator)
  - whether the content is *correct*  (that is grade.py's job)

How it works mechanically: llama-server accepts `json_schema` in the /completion request body and
builds the grammar server-side. Grammar sampling has a per-token cost - a Phase 2 finding to measure.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import NoteAnswer, ProcessedNote  # noqa: E402

Enforcement = Literal["prompt_only", "json_object", "json_schema"]
MODES: tuple[str, ...] = ("prompt_only", "json_object", "json_schema")


ANNOTATION_KEYS = ("title", "description", "default")


def _clean(node):
    """Drop documentation-only keywords (title/description/default) from schema nodes.

    Careful: inside "properties" and "$defs" the keys are FIELD NAMES, not keywords - our schemas
    have real fields called "title" and "description". Stripping those removed the fields from the
    grammar (bug found by the Phase 2 smoke test; guarded by tests/test_enforcement.py).
    """
    if isinstance(node, list):
        return [_clean(v) for v in node]
    if not isinstance(node, dict):
        return node
    out = {}
    for key, value in node.items():
        if key in ("properties", "$defs") and isinstance(value, dict):
            out[key] = {name: _clean(sub) for name, sub in value.items()}   # names kept as-is
        elif key in ANNOTATION_KEYS:
            continue
        else:
            out[key] = _clean(value)
    return out


def schema_for(track: str, n_chunks: Optional[int] = None) -> dict:
    if track == "A":
        return _clean(ProcessedNote.model_json_schema())
    schema = _clean(NoteAnswer.model_json_schema())
    if n_chunks:
        # We know exactly how many chunks were shown, so the grammar can make citing a
        # non-existent chunk impossible (this removes the 'context' error type entirely).
        schema = copy.deepcopy(schema)
        schema["properties"]["source_chunk_ids"]["items"].update({"minimum": 0, "maximum": n_chunks - 1})
    return schema


def enforcement_params(mode: str, track: str, n_chunks: Optional[int] = None) -> dict:
    """Extra /completion request fields for a given mode and track."""
    if mode == "prompt_only":
        return {}
    if mode == "json_object":
        return {"json_schema": {"type": "object"}}
    if mode == "json_schema":
        return {"json_schema": schema_for(track, n_chunks)}
    raise ValueError(f"unknown enforcement mode {mode!r}; choose from {MODES}")
