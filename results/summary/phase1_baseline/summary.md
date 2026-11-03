# Phase 1 summary - phase1_qwen3-4b-instruct_q4km_20261029-144931

Runs: phase1_qwen3-4b-instruct_q4km_20261029-144931, phase1_qwen3-4b-instruct_q4km_20261029-154046  
Requests analysed: 476 (excluded 6 warm-up, 0 errors, first 15 requests of each run)  
Model: qwen3-4b-instruct-2507 Q4_K_M - temperature 0.0

| Track | n | TTFT median (ms) | TTFT p95 (ms) | Prefill median (tok/s) | Decode median (tok/s) | Decode std | Latency median (ms) | Latency p95 (ms) | Input tok (median) | Output tok (median) | JSON parses |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 236 | 229 | 317 | 2323 | 73.1 | 3.6 | 2983 | 4081 | 407 | 199 | 100% |
| B | 240 | 301 | 445 | 2385 | 71.2 | 4.7 | 1051 | 1479 | 559 | 54 | 100% |
| all | 476 | 273 | 371 | 2357 | 72.5 | 4.4 | 1589 | 3870 | 518 | 93 | 100% |

Identical output across repeats (determinism preview): Track A: 100%, Track B: 100%

## Reproducibility (median per run, % vs first run)

| run_id                                        |   ttft_ms |   prefill_tps |   decode_tps |   latency_ms |
|:----------------------------------------------|----------:|--------------:|-------------:|-------------:|
| phase1_qwen3-4b-instruct_q4km_20261029-144931 |       0   |           0   |          0   |          0   |
| phase1_qwen3-4b-instruct_q4km_20261029-154046 |       3.2 |          -2.9 |         -4.2 |          7.1 |
