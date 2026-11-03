# Benchmark harness

One runner for every phase. Each experiment is one YAML config in `configs/`, and each run writes raw,
never-edited rows to `results/raw/`. All tables and charts are recomputed from those rows.

## Setup (once, in the project venv)

```bash
cd "/d/SLM Project"
source second_brain_corpus/.venv/Scripts/activate
pip install -r harness/requirements.txt
```

## Phase 1 run

1. Laptop plugged in, Best-performance power mode, heavy apps closed.
2. Window 1 - start the server (leave it running):
   ```bash
   ./llama-bin/llama-server.exe -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M -ngl 99 -c 8192 --port 8080 --seed 42
   ```
3. Window 2 - smoke test, then the full run, then analysis:
   ```bash
   python harness/runner.py --config configs/phase1_pilot.yaml --limit 4 --repeats 1   # ~10 s sanity check
   python harness/runner.py --config configs/phase1_pilot.yaml                          # 50 x 5 + 3 warm-up
   python harness/analyze_phase1.py results/raw/<run>.jsonl
   ```
4. Reproducibility check: run the full suite a second time, then pass both files:
   ```bash
   python harness/analyze_phase1.py results/raw/<run1>.jsonl results/raw/<run2>.jsonl
   ```
   Phase 1 is done when medians drift < ~5% between runs.

## What each row contains

| Field | Meaning |
|---|---|
| `ttft_ms` | client-side: request sent -> first streamed token (includes HTTP + prefill) |
| `prompt_n`, `prompt_ms`, `prefill_tps` | server-side prompt processing |
| `predicted_n`, `predicted_ms`, `decode_tps` | server-side generation |
| `latency_ms` | client-side end-to-end |
| `stop_type` | `eos` (finished) or `limit` (hit `n_predict` - check these) |
| `output_text` | the raw model output, graded later in Phase 2 |
| `gpu_*` | nvidia-smi sample after each request (throttling check) |
| `is_warmup`, `repeat`, `seq` | run bookkeeping; warm-up rows are excluded from analysis |

Prompt caching is disabled (`cache_prompt: false`) so every request pays the full prefill.
`prompts.py` has a `PROMPT_VERSION`; bump it whenever a prompt changes.
