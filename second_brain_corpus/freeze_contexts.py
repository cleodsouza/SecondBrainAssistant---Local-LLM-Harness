"""
Run retrieval ONCE for every Track B question and freeze the top-k chunks to disk.

    pip install chromadb sentence-transformers
    python build_corpus.py          # first
    python freeze_contexts.py

Writes
    build/track_b_frozen.jsonl   - each question + its exact top-k context chunks + gold_in_topk flag
    build/retrieval_config.json  - the held-constant retrieval settings + recall@k (paste into the report)

Every model / temperature / quant level in Phases 1-4 reads track_b_frozen.jsonl, so the context
is byte-identical across runs. Re-run this script only if the corpus changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
BUILD = ROOT / "build"

# ---- Held-constant retrieval configuration -------------------------------------------------
EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # one small CPU-friendly embedder, never changed
TOP_K = 4
CHUNK_WORDS = 200        # notes longer than this are split on paragraph boundaries
DISTANCE = "cosine"
# bge models recommend this prefix on queries (not on passages)
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
# ---------------------------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def chunk_note(note: dict) -> list[dict]:
    """One note = one chunk, unless it is long; then greedily pack paragraphs up to CHUNK_WORDS."""
    header = f"[{note['id']} | {note['created']}]"   # date in the text lets models answer temporal questions
    paras = [p.strip() for p in note["body"].split("\n\n") if p.strip()]
    chunks, buf = [], []
    for p in paras:
        if buf and len(" ".join(buf + [p]).split()) > CHUNK_WORDS:
            chunks.append(buf)
            buf = []
        buf.append(p)
    if buf:
        chunks.append(buf)
    return [
        {"chunk_key": f"{note['id']}#{i}", "note_id": note["id"], "created": note["created"],
         "text": f"{header}\n" + "\n\n".join(c)}
        for i, c in enumerate(chunks)
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", default=str(BUILD / "chroma"), help="Chroma directory (reused by the demo app)")
    args = ap.parse_args()

    import chromadb
    from sentence_transformers import SentenceTransformer

    notes = read_jsonl(BUILD / "notes.jsonl")
    questions = read_jsonl(BUILD / "track_b.jsonl")
    chunks = [c for n in notes for c in chunk_note(n)]

    embedder = SentenceTransformer(EMBED_MODEL)
    doc_vecs = embedder.encode([c["text"] for c in chunks], normalize_embeddings=True).tolist()

    client = chromadb.PersistentClient(path=args.persist)
    try:
        client.delete_collection("notes")
    except Exception:
        pass
    col = client.create_collection("notes", metadata={"hnsw:space": DISTANCE})
    col.add(
        ids=[c["chunk_key"] for c in chunks],
        embeddings=doc_vecs,
        documents=[c["text"] for c in chunks],
        metadatas=[{"note_id": c["note_id"], "created": c["created"]} for c in chunks],
    )

    q_vecs = embedder.encode([QUERY_PREFIX + q["question"] for q in questions], normalize_embeddings=True).tolist()

    hits_total, answerable_total = 0, 0
    out_path = BUILD / "track_b_frozen.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for q, vec in zip(questions, q_vecs):
            res = col.query(query_embeddings=[vec], n_results=TOP_K)
            context = [
                {"chunk_id": i, "chunk_key": key, "note_id": meta["note_id"],
                 "score": round(1 - dist, 4), "text": doc}
                for i, (key, doc, meta, dist) in enumerate(zip(
                    res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]))
            ]
            retrieved = {c["note_id"] for c in context}
            gold = set(q["gold_note_ids"])
            gold_in_topk = gold <= retrieved if gold else None     # None for unanswerable items
            # chunk_ids (0..k-1) a correct answer should cite - used to score grounding
            gold_chunk_ids = [c["chunk_id"] for c in context if c["note_id"] in gold]
            if q["answerable"]:
                answerable_total += 1
                hits_total += bool(gold_in_topk)
            f.write(json.dumps({**q, "context_chunks": context, "gold_in_topk": gold_in_topk,
                                "gold_chunk_ids": gold_chunk_ids}, ensure_ascii=False) + "\n")

    recall = hits_total / answerable_total if answerable_total else 0.0
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()[:12]
    config = {
        "vector_store": "chromadb", "embedding_model": EMBED_MODEL, "top_k": TOP_K,
        "chunking": f"one note per chunk; notes > {CHUNK_WORDS} words split on paragraphs",
        "distance": DISTANCE, "reranking": None, "hybrid_search": False,
        "n_notes": len(notes), "n_chunks": len(chunks),
        f"recall@{TOP_K}_answerable": round(recall, 3),
        "frozen_file_sha256_12": digest,
    }
    (BUILD / "retrieval_config.json").write_text(json.dumps(config, indent=2))

    print(json.dumps(config, indent=2))
    misses = [q["id"] for q in read_jsonl(out_path) if q["gold_in_topk"] is False]
    if misses:
        print(f"Gold note missing from top-{TOP_K} for: {misses}  (tag these 'retrieval_miss' in error analysis)")


if __name__ == "__main__":
    main()
