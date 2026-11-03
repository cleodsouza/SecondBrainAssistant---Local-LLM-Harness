"""
Prompt builders for both tracks.

The prompts are versioned (PROMPT_VERSION) and the version is written into every result row,
so a prompt change never silently mixes with older results. Bump it whenever you edit a prompt.
"""
from __future__ import annotations

PROMPT_VERSION = "v1"

TAGS = ("work, design, engineering, career, learning, reading, health, fitness, finance, travel, "
        "family, friends, home, side-project, writing, productivity, music, food, admin, events")

TRACK_A_SYSTEM = f"""You are a personal knowledge assistant. You turn one raw personal note into structured JSON.

Return ONLY a JSON object with exactly these keys:
- "title": short title, max 80 characters
- "note_type": one of "idea", "meeting", "journal", "reading", "todo", "reference"
- "tags": 1 to 4 tags, chosen ONLY from: {TAGS}
- "summary": at most 2 sentences
- "action_items": list of {{"description": str, "due": "YYYY-MM-DD" or null, "priority": "low" | "medium" | "high"}}
- "entities": named people, projects, products, books, organisations and places mentioned

Rules:
- Resolve relative dates ("by Friday", "Sunday", "end of November") against the note's created date.
- Vague ranges ("this week", "next week", "in November", "sometime") get "due": null.
- Include tasks assigned to other people, prefixed with the owner, e.g. "Kabir: submit the application".
- Instructions from a doctor or physio count as action items. Events that simply happen are not action items.
- If the note has no tasks, return "action_items": []. Never invent tasks.
- No markdown, no code fences, no text outside the JSON object."""

TRACK_B_SYSTEM = """You are a personal knowledge assistant. You answer questions about the user's own notes,
using ONLY the numbered note chunks provided. Each chunk starts with its note id and the date it was written.

Return ONLY a JSON object with exactly these keys:
- "answerable": true if the chunks contain the answer, otherwise false
- "answer": a short answer in 1-2 sentences, or null when answerable is false
- "source_chunk_ids": list of chunk numbers (integers) that contain the answer; [] when answerable is false
- "confidence": "low", "medium" or "high"

Rules:
- Do not use outside knowledge and do not guess. If the chunks do not contain the answer, set
  "answerable": false and "answer": null.
- A plan to do something is not evidence that it was done.
- For date arithmetic, use the "Today" date given with the question.
- No markdown, no code fences, no text outside the JSON object."""


def track_a_messages(note: dict) -> list[dict]:
    user = f"Note created: {note['created']}\n\n{note['body'].strip()}"
    return [{"role": "system", "content": TRACK_A_SYSTEM}, {"role": "user", "content": user}]


def track_b_messages(item: dict) -> list[dict]:
    chunks = "\n\n".join(f"Chunk {c['chunk_id']}:\n{c['text'].strip()}" for c in item["context_chunks"])
    user = f"{chunks}\n\nToday: {item['asked_on']}\nQuestion: {item['question']}"
    return [{"role": "system", "content": TRACK_B_SYSTEM}, {"role": "user", "content": user}]
