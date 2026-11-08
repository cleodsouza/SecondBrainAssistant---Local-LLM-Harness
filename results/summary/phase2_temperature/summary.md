# Phase 2.5 - temperature sweep (temperature)

Runs: 12  |  graded rows: 1800  |  seeds used: [43, 44, 45]  |  model: qwen3-4b-instruct-2507 Q4_K_M

Quality = Track A field_score / Track B qa_score (failed outputs score 0). Identical = same output text across repeats; Agreement = same key decision across repeats.

| Mode | Filters | Temp | Track | n | First-try valid | Final valid | Quality | Hallucination | Identical | Agreement | Latency med / p95 (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| json_schema | off | 0.7 | A | 75 | 93% | 100% | 64% | - | 0% | 20% | 3,796 / 6,762 |
| json_schema | off | 0.7 | B | 75 | 100% | 100% | 96% | 0% | 52% | 100% | 1,266 / 1,767 |
| json_schema | on | 0.0 | A | 75 | 92% | 100% | 65% | - | 100% | 100% | 3,150 / 6,182 |
| json_schema | on | 0.0 | B | 75 | 100% | 100% | 96% | 0% | 100% | 100% | 1,057 / 1,556 |
| json_schema | on | 0.2 | A | 75 | 91% | 100% | 64% | - | 12% | 64% | 3,507 / 6,721 |
| json_schema | on | 0.2 | B | 75 | 100% | 100% | 96% | 0% | 80% | 100% | 1,193 / 1,697 |
| json_schema | on | 0.4 | A | 75 | 95% | 100% | 64% | - | 0% | 40% | 3,466 / 5,364 |
| json_schema | on | 0.4 | B | 75 | 100% | 100% | 96% | 0% | 72% | 100% | 1,190 / 1,668 |
| json_schema | on | 0.6 | A | 75 | 93% | 100% | 63% | - | 0% | 16% | 3,415 / 6,610 |
| json_schema | on | 0.6 | B | 75 | 100% | 100% | 96% | 0% | 68% | 100% | 1,178 / 1,650 |
| json_schema | on | 0.7 | A | 75 | 97% | 100% | 64% | - | 0% | 16% | 3,487 / 4,840 |
| json_schema | on | 0.7 | B | 75 | 100% | 100% | 96% | 0% | 60% | 100% | 1,198 / 1,682 |
| prompt_only | off | 0.7 | A | 75 | 52% | 83% | 54% | - | 8% | 28% | 4,367 / 8,548 |
| prompt_only | off | 0.7 | B | 75 | 100% | 100% | 96% | 0% | 52% | 100% | 1,079 / 1,502 |
| prompt_only | on | 0.0 | A | 75 | 48% | 80% | 54% | - | 100% | 100% | 4,943 / 7,625 |
| prompt_only | on | 0.0 | B | 75 | 100% | 100% | 96% | 0% | 100% | 100% | 1,012 / 1,386 |
| prompt_only | on | 0.2 | A | 75 | 51% | 84% | 55% | - | 12% | 56% | 4,391 / 7,769 |
| prompt_only | on | 0.2 | B | 75 | 100% | 100% | 96% | 0% | 80% | 100% | 1,017 / 1,451 |
| prompt_only | on | 0.4 | A | 75 | 57% | 85% | 56% | - | 8% | 44% | 4,072 / 8,638 |
| prompt_only | on | 0.4 | B | 75 | 100% | 100% | 96% | 0% | 72% | 100% | 1,139 / 1,592 |
| prompt_only | on | 0.6 | A | 75 | 49% | 84% | 55% | - | 8% | 28% | 4,955 / 8,352 |
| prompt_only | on | 0.6 | B | 75 | 100% | 100% | 96% | 0% | 68% | 100% | 1,069 / 1,500 |
| prompt_only | on | 0.7 | A | 75 | 55% | 85% | 56% | - | 8% | 24% | 3,972 / 7,907 |
| prompt_only | on | 0.7 | B | 75 | 100% | 100% | 96% | 0% | 60% | 100% | 1,023 / 1,447 |

Charts: *_vs_temperature.png
