# Phase 2 summary - enforcement

Runs: 6  |  items analysed: 900 (warm-up excluded)  |  model: qwen3-4b-instruct-2507 Q4_K_M  |  max_retries: 1

| Enforcement | Temp | Track | n | First-try valid | Needed retry | Rescued | Final valid | Attempt-1 errors (empty/not_json/schema/context) | Decode tok/s | Latency med (ms) | Total med / p95 (ms) | Identical across repeats |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prompt_only | 0.0 | A | 75 | 48% | 52% | 62% | 80% | 0/0/39/0 | 75.0 | 2906 | 4918 / 7746 | 100% |
| prompt_only | 0.0 | B | 75 | 100% | 0% | - | 100% | 0/0/0/0 | 73.5 | 1020 | 1020 / 1364 | 100% |
| prompt_only | 0.7 | A | 75 | 44% | 56% | 64% | 80% | 0/0/42/0 | 76.4 | 2969 | 5121 / 7184 | 100% |
| prompt_only | 0.7 | B | 75 | 100% | 0% | - | 100% | 0/0/0/0 | 74.5 | 991 | 991 / 1391 | 100% |
| json_object | 0.0 | A | 75 | 48% | 52% | 62% | 80% | 0/0/39/0 | 74.4 | 2964 | 4993 / 7692 | 100% |
| json_object | 0.0 | B | 75 | 100% | 0% | - | 100% | 0/0/0/0 | 73.3 | 1004 | 1004 / 1380 | 100% |
| json_object | 0.7 | A | 75 | 44% | 56% | 64% | 80% | 0/0/42/0 | 74.5 | 3008 | 5381 / 7468 | 100% |
| json_object | 0.7 | B | 75 | 100% | 0% | - | 100% | 0/0/0/0 | 73.6 | 1008 | 1008 / 1369 | 100% |
| json_schema | 0.0 | A | 75 | 92% | 8% | 100% | 100% | 0/0/6/0 | 73.4 | 2983 | 2993 / 5775 | 100% |
| json_schema | 0.0 | B | 75 | 100% | 0% | - | 100% | 0/0/0/0 | 71.1 | 1023 | 1023 / 1506 | 100% |
| json_schema | 0.7 | A | 75 | 92% | 8% | 100% | 100% | 0/0/6/0 | 74.1 | 3037 | 3041 / 5405 | 100% |
| json_schema | 0.7 | B | 75 | 100% | 0% | - | 100% | 0/0/0/0 | 71.5 | 1026 | 1026 / 1406 | 100% |

Attempt-1 error examples: error_examples.md  |  charts: *.png
