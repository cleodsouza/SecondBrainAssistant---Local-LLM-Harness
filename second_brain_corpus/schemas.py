"""
Schemas for the Second Brain benchmark.

Two kinds of models live here:
  1. OUTPUT schemas  - what the SLM must produce (ProcessedNote, NoteAnswer).
                       These are what Phase 2 validates with Pydantic.
  2. CORPUS schemas  - how the dataset itself is stored (Note, TrackAItem, TrackBItem).

Vocabularies are FIXED on purpose: a closed tag/type set keeps grading objective.
"""
from __future__ import annotations

import re
from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Fixed vocabularies
# ---------------------------------------------------------------------------
NoteType = Literal["idea", "meeting", "journal", "reading", "todo", "reference"]

TAG_VOCAB: tuple[str, ...] = (
    "work", "design", "engineering", "career", "learning", "reading",
    "health", "fitness", "finance", "travel", "family", "friends",
    "home", "side-project", "writing", "productivity", "music", "food",
    "admin", "events",
)
Tag = Literal[
    "work", "design", "engineering", "career", "learning", "reading",
    "health", "fitness", "finance", "travel", "family", "friends",
    "home", "side-project", "writing", "productivity", "music", "food",
    "admin", "events",
]

Priority = Literal["low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]

MAX_TAGS = 4

_ABBREV = re.compile(r"\b(?:Dr|Mr|Mrs|Ms|vs|etc|e\.g|i\.e|approx|no)\.", re.IGNORECASE)
_SENT_END = re.compile(r"[.!?]+(?=\s|$)")


def count_sentences(text: str) -> int:
    """Count sentence terminators followed by whitespace/end, ignoring 'Dr.', 'v0.1', 'crates.io' etc."""
    cleaned = _ABBREV.sub("ABBR", text.strip())
    return max(1, len(_SENT_END.findall(cleaned))) if cleaned else 0


# ---------------------------------------------------------------------------
# OUTPUT schemas (what the model must return)
# ---------------------------------------------------------------------------
class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=3)
    due: Optional[date] = None          # ISO date; relative dates resolved against note's created date
    priority: Priority = "medium"


class ProcessedNote(BaseModel):
    """Track A output: one raw note in -> this object out."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=80)
    note_type: NoteType
    tags: list[Tag] = Field(min_length=1, max_length=MAX_TAGS)
    summary: str = Field(min_length=10, max_length=300)   # <= 2 sentences, enforced below
    action_items: list[Task] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)      # people, projects, books, places, orgs

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("tags must be unique")
        return v

    @field_validator("summary")
    @classmethod
    def max_two_sentences(cls, v: str) -> str:
        if count_sentences(v) > 2:
            raise ValueError("summary must be at most 2 sentences")
        return v


class NoteAnswer(BaseModel):
    """Track B output: question + frozen top-k chunks in -> this object out."""
    model_config = ConfigDict(extra="forbid")

    answerable: bool
    answer: Optional[str]
    source_chunk_ids: list[int] = Field(default_factory=list)  # indices into the provided chunks
    confidence: Confidence

    @model_validator(mode="after")
    def consistency(self) -> "NoteAnswer":
        if self.answerable and not self.answer:
            raise ValueError("answer is required when answerable is true")
        if self.answerable and not self.source_chunk_ids:
            raise ValueError("cite at least one source_chunk_id when answerable is true")
        if not self.answerable and self.answer:
            raise ValueError("answer must be null when answerable is false")
        return self

    def check_chunk_ids(self, n_chunks: int) -> None:
        """Call at runtime with the number of chunks actually shown to the model."""
        bad = [i for i in self.source_chunk_ids if not 0 <= i < n_chunks]
        if bad:
            raise ValueError(f"source_chunk_ids out of range: {bad} (only {n_chunks} chunks given)")


# ---------------------------------------------------------------------------
# CORPUS schemas (how the dataset is stored)
# ---------------------------------------------------------------------------
Difficulty = Literal["easy", "medium", "hard"]


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^n\d{3}$")
    created: date
    body: str = Field(min_length=10)
    edge_case: Optional[str] = None   # e.g. "no_action_items", "hinglish", "vague_date", "long_note"


class TrackAItem(BaseModel):
    """Note-processing prompt: input is note `note_id`, expected is the gold ProcessedNote."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^a\d{3}$")
    note_id: str
    difficulty: Difficulty
    expected: ProcessedNote


class TrackBItem(BaseModel):
    """Ask-my-notes prompt. Context is filled in later by freeze_contexts.py."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^b\d{3}$")
    question: str
    asked_on: date                      # "today" for the question, for relative-date questions
    difficulty: Difficulty
    answerable: bool
    gold_note_ids: list[str] = Field(default_factory=list)   # notes that contain the answer
    expected_answer: Optional[str] = None                       # reference answer (for judge / rubric)
    key_facts: list[str] = Field(default_factory=list)       # short strings a correct answer must contain
    question_type: Literal["lookup", "multi_note", "temporal", "aggregation", "unanswerable"]

    @model_validator(mode="after")
    def consistency(self) -> "TrackBItem":
        if self.answerable:
            if not (self.gold_note_ids and self.expected_answer and self.key_facts):
                raise ValueError(f"{self.id}: answerable items need gold_note_ids, expected_answer, key_facts")
        else:
            if self.expected_answer or self.key_facts:
                raise ValueError(f"{self.id}: unanswerable items must not have an expected answer")
        return self
