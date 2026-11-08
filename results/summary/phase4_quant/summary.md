# Phase 4 - quantization study (Granite 4.1 3B)

Runs: 22 | graded rows: 1100 | schema mode, temperature 0, one retry, llama.cpp b11954, -np 1, -c 4096. * = imatrix-calibrated, (u) = unsloth's file.

| Version | Size (GB) | Bits/weight | Size vs BF16 | VRAM (GB) | Decode tok/s | Speed-up | Latency A / B (ms) | A first-try valid | A quality | Δ vs BF16 | B quality | Δ vs BF16 | Halluc. | KLD | Same top token | PPL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BF16 | 6.81 | 16.00 | 100% | 6.90 | 40.9 | 1.00x | 4,179 / 1,338 | 88% | 61% | +0 pts | 92% | +0 pts | 0% | 0.0000 | 100.0% | 13.72 |
| Q8_0 | 3.62 | 8.50 | 53% | 3.93 | 62.7 | 1.53x | 2,727 / 963 | 88% | 60% | -2 pts | 92% | +0 pts | 0% | 0.0020 | 97.9% | 13.74 |
| Q6_K | 2.80 | 6.57 | 41% | 3.17 | 68.5 | 1.68x | 2,630 / 880 | 88% | 57% | -4 pts | 92% | +0 pts | 0% | 0.0097 | 94.5% | 13.85 |
| Q5_K_M | 2.44 | 5.73 | 36% | 2.84 | 73.0 | 1.79x | 2,517 / 851 | 84% | 52% | -9 pts | 88% | -4 pts | 0% | 0.0354 | 89.9% | 14.15 |
| Q4_K_M | 2.10 | 4.93 | 31% | 2.53 | 81.5 | 1.99x | 2,252 / 781 | 60% | 48% | -13 pts | 88% | -4 pts | 0% | 0.0906 | 83.5% | 14.87 |
| Q3_K_M | 1.73 | 4.05 | 25% | 2.16 | 79.4 | 1.94x | 1,684 / 967 | 84% | 54% | -8 pts | 88% | -4 pts | 17% | 0.2800 | 73.6% | 18.36 |
| Q2_K | 1.37 | 3.22 | 20% | 1.83 | 91.4 | 2.24x | 1,293 / 1,147 | 80% | 25% | -36 pts | 24% | -68 pts | 0% | 1.2406 | 50.6% | 42.47 |
| Q4_K_M* | 2.10 | 4.93 | 31% | 2.52 | 80.1 | 1.96x | 2,097 / 757 | 88% | 61% | -1 pts | 88% | -4 pts | 0% | 0.0359 | 90.7% | 13.69 |
| Q3_K_M* | 1.73 | 4.05 | 25% | 2.18 | 80.0 | 1.96x | 1,990 / 765 | 68% | 52% | -9 pts | 84% | -8 pts | 0% | 0.1130 | 82.0% | 14.81 |
| Q2_K* | 1.37 | 3.22 | 20% | 1.83 | 98.9 | 2.42x | 1,638 / 747 | 88% | 62% | +1 pts | 92% | +0 pts | 17% | 0.3201 | 72.1% | 17.34 |
| Q4_K_M (u) | 2.10 | 4.93 | 31% | 2.52 | 79.6 | 1.95x | 2,125 / 769 | 84% | 58% | -4 pts | 92% | +0 pts | 0% | 0.0349 | 90.7% | 13.73 |

## Track A accuracy by field

```
                        note_type  tags  actions_f1  due_acc  entities_f1
model                                                                    
granite-BF16                 64.0  42.0        77.0     63.0         62.0
granite-Q8_0                 64.0  43.0        76.0     57.0         60.0
granite-Q6_K                 60.0  42.0        68.0     53.0         64.0
granite-Q5_K_M               56.0  43.0        63.0     44.0         56.0
granite-Q4_K_M               44.0  31.0        59.0     53.0         56.0
granite-Q3_K_M               52.0  37.0        76.0     58.0         45.0
granite-Q2_K                 16.0  31.0        33.0     20.0         25.0
granite-Q4_K_M-imat          60.0  39.0        78.0     64.0         63.0
granite-Q3_K_M-imat          48.0  36.0        71.0     46.0         59.0
granite-Q2_K-imat            64.0  37.0        80.0     67.0         63.0
granite-Q4_K_M-unsloth       56.0  41.0        73.0     64.0         54.0
```

Charts: quality_vs_size.png, qa_quality_vs_size.png, speed_vs_size.png, kld_vs_bpw.png, field_heatmap.png
