# Phase 3 - model comparison

Runs: 24 | graded rows: 1200 | models: gemma-4-e4b-it, granite-4.1-3b, phi-4-mini-instruct, qwen3-4b-instruct-2507 | temperature 0, one retry, llama.cpp b11954, -np 1, -c 8192

## Speed and memory (json_schema mode)

| Model | Quant | Model VRAM (GB) | Peak VRAM (GB) | Server RAM peak (GB) | Decode tok/s | Prefill tok/s | TTFT A / B (ms) | Latency A / B (ms) | Input tokens A / B |
|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b-it | Q4_K_M | 3.32 | 3.35 | 4.91 | 50.5 | 1,648 | 274 / 397 | 2,839 / 1,439 | 426 / 587 |
| granite-4.1-3b | Q4_K_M | 2.85 | 2.87 | 3.60 | 71.0 | 2,584 | 194 / 250 | 2,397 / 892 | 400 / 525 |
| phi-4-mini-instruct | Q4_K_M | 3.58 | 3.60 | 4.83 | 67.4 | 2,734 | 211 / 252 | 2,306 / 975 | 390 / 507 |
| qwen3-4b-instruct-2507 | Q4_K_M | 3.71 | 3.73 | 5.25 | 64.1 | 2,321 | 246 / 320 | 3,380 / 1,178 | 407 / 559 |

Model VRAM = GPU memory after load minus GPU memory before the server started. Server RAM = peak resident memory of llama-server (includes memory-mapped model pages and any weights llama.cpp keeps on the CPU, e.g. Gemma's per-layer embedding tables). Compare both, not VRAM alone.

## Structure and quality

| Model | Mode | A first-try valid | A final valid | A quality | Invented tasks | B quality | B hallucination | Reproducible across restarts |
|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b-it | json_schema | 100% | 100% | 73% | 4% | 96% | 0% | 100% |
| granite-4.1-3b | json_schema | 84% | 88% | 58% | 0% | 92% | 0% | 100% |
| phi-4-mini-instruct | json_schema | 76% | 88% | 47% | 12% | 84% | 17% | 100% |
| qwen3-4b-instruct-2507 | json_schema | 92% | 100% | 65% | 8% | 96% | 0% | 100% |
| gemma-4-e4b-it | prompt_only | 56% | 80% | 58% | 4% | 96% | 0% | 100% |
| granite-4.1-3b | prompt_only | 60% | 88% | 58% | 0% | 84% | 0% | 100% |
| phi-4-mini-instruct | prompt_only | 56% | 84% | 45% | 12% | 64% | 17% | 100% |
| qwen3-4b-instruct-2507 | prompt_only | 48% | 80% | 54% | 4% | 96% | 0% | 100% |

## Efficiency (json_schema mode)

| Model | A quality per GB VRAM | A quality per second (Track A latency) |
|---|---|---|
| gemma-4-e4b-it | 22.0 pts/GB | 25.7 pts/s |
| granite-4.1-3b | 20.2 pts/GB | 24.0 pts/s |
| phi-4-mini-instruct | 13.0 pts/GB | 20.3 pts/s |
| qwen3-4b-instruct-2507 | 17.4 pts/GB | 19.1 pts/s |

## Track A accuracy by field (json_schema)

```
                        note_type  tags  actions_f1  due_acc  entities_f1
model                                                                    
gemma-4-e4b-it               76.0  46.0        89.0     83.0         72.0
granite-4.1-3b               56.0  41.0        73.0     64.0         54.0
phi-4-mini-instruct          52.0  41.0        60.0     33.0         47.0
qwen3-4b-instruct-2507       64.0  47.0        78.0     70.0         63.0
```

Charts: *.png in this folder
