"""Tests for harness/enforcement.py.  Run:  python -m pytest harness/tests -v"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from enforcement import enforcement_params, schema_for  # noqa: E402
from validate import NoteAnswer, ProcessedNote  # noqa: E402


def _all_object_nodes(node):
    if isinstance(node, dict):
        if "properties" in node:
            yield node
        for v in node.values():
            yield from _all_object_nodes(v)
    elif isinstance(node, list):
        for v in node:
            yield from _all_object_nodes(v)


@pytest.mark.parametrize("track,model", [("A", ProcessedNote), ("B", NoteAnswer)])
def test_grammar_schema_keeps_every_field(track, model):
    """Regression: fields literally named 'title' / 'description' must survive cleaning."""
    s = schema_for(track, 4)
    assert set(s["properties"]) == set(model.model_fields)
    if track == "A":
        assert "title" in s["properties"]
        assert "description" in s["$defs"]["Task"]["properties"]


@pytest.mark.parametrize("track", ["A", "B"])
def test_required_fields_all_defined(track):
    """Every 'required' name must exist in that node's properties, or the grammar is inconsistent."""
    for node in _all_object_nodes(schema_for(track, 4)):
        assert set(node.get("required", [])) <= set(node["properties"])


def test_annotations_removed():
    s = schema_for("A")
    assert "title" not in s["properties"]["title"]          # the keyword, not the field
    assert "default" not in s["$defs"]["Task"]["properties"]["due"]


def test_chunk_ids_bounded_for_track_b():
    item = schema_for("B", 4)["properties"]["source_chunk_ids"]["items"]
    assert item["minimum"] == 0 and item["maximum"] == 3


def test_modes():
    assert enforcement_params("prompt_only", "A") == {}
    assert enforcement_params("json_object", "A") == {"json_schema": {"type": "object"}}
    assert "properties" in enforcement_params("json_schema", "B", 4)["json_schema"]
    with pytest.raises(ValueError):
        enforcement_params("bogus", "A")
