# Second Brain Assistant — Local LLM Benchmarking & Reliability Harness

A local small-language-model assistant for personal notes, used as a testbed to measure and improve
**speed, structure and reliability** of on-device LLM inference (llama.cpp, consumer GPU).

## Phases
| Phase | Focus | Status |
|---|---|---|
| 1 | Measurement — TTFT, prefill/decode tok/s, latency, run-to-run variance | Done |
| 2 | Structure & determinism — JSON schema, Pydantic validation, one error-guided retry, enforcement modes, temperature | In progress |
| 3 | Model comparison — 3 SLMs on memory, speed and quality | Planned |
| 4 | Quantization — GGUF F16 → Q2_K, speed vs quality trade-off | Planned |

## Results so far (Qwen3-4B-Instruct-2507, Q4_K_M, RTX 3070 Ti Laptop 8 GB, llama.cpp b11954)
- **Baseline:** ~73 tok/s decode; median TTFT 228 ms (note processing) / 298 ms (Q&A); latency is decode-bound.
  Run-to-run variance on the laptop: ±4–7%.
- **Structure:** outputs were 100% parseable JSON but only **48% schema-valid** on note extraction.
  Grammar-constrained decoding (JSON schema → GBNF) raised first-try validity to **92%** and final validity to
  **100%**, and cut median latency from 4.9 s to 3.0 s by avoiding retries.

Full record of decisions and numbers: [`PROJECT_LOG.md`](PROJECT_LOG.md).

## Layout
```
second_brain_corpus/   synthetic notes, labelled Track A/B items, Pydantic schemas, frozen retrieval contexts
harness/               runner (streaming + timings), validation, retry wrapper, enforcement modes, analysis
  tests/               42 unit tests (pytest)
configs/               one YAML per experiment
results/raw/           one JSONL row per generation (never edited)
results/summary/       tables, charts, error examples
```

## Reproduce
```bash
python -m venv second_brain_corpus/.venv && source second_brain_corpus/.venv/Scripts/activate
pip install -r harness/requirements.txt chromadb sentence-transformers
python second_brain_corpus/build_corpus.py && python second_brain_corpus/freeze_contexts.py
# start llama-server (llama.cpp CUDA build) with the GGUF model on port 8080, then:
python -m pytest harness/tests -q
bash run_phase1.sh
bash run_phase2_enforcement.sh
```
