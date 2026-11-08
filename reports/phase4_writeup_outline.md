# Phase 4 write-up — outline (quantization)

Skeleton for **you** to write in your own words (2–3 pages). Model: Granite 4.1 3B (IBM), 11 versions,
llama.cpp b11954, RTX 3070 Ti Laptop (8 GB), Turbo, temperature 0, schema mode, one retry, `-np 1 -c 4096`,
50 items × 2 rounds = 1,100 graded outputs + KL divergence vs BF16 on the 60 notes (~3.4k tokens).
Summary: `results/summary/phase4_quant/summary.md`.

---

## 4.1 Goal (1 paragraph)
- How much speed and memory does quantization buy, what does it cost in quality, and does calibration
  (importance matrix) change the answer? Is a self-made quantization as good as a downloaded one?

## 4.2 Setup (½ page)
- Why Granite: official BF16 GGUF (6.81 GB) fits the 8 GB GPU → a true unquantized baseline on GPU.
- Versions: BF16; our plain Q8_0 / Q6_K / Q5_K_M / Q4_K_M / Q3_K_M / Q2_K (`llama-quantize`);
  our calibrated Q4_K_M / Q3_K_M / Q2_K (`--imatrix`, unsloth's matrix computed on *their* calibration text,
  not our notes → no contamination); unsloth's own Q4_K_M.
- Calibration does not change size (Q2_K = 1,304.5 MiB / 3.22 bpw either way) — it changes *which* weights keep precision.
- Two independent quality views: our task grader, and **KL divergence** (how far each version's next-token
  probabilities drift from BF16) + same-top-token rate + perplexity via `llama-perplexity`.
- Same Phase 3 runner: server restart per version, file check, interleaved rounds, memory sampler.

## 4.3 A measurement problem worth reporting (short)
- Smoke test at `-c 8192`: BF16 used 7.5 of 8 GB, Windows silently spilled to system RAM — GPU 97% busy at
  a 210 MHz clock, 17 tok/s (vs 42 tok/s with headroom). Fix: `-c 4096` for all versions; analysis now flags
  any version whose GPU clock collapses. Lesson: on Windows, "fits in VRAM" needs real headroom.

## 4.4 Results — speed and memory
| Version | Size vs BF16 | VRAM (GB) | Decode tok/s | Speed-up |
|---|---|---|---|---|
| BF16 | 100% | 6.90 | 40.9 | 1.0× |
| Q8_0 | 53% | 3.93 | 62.7 | 1.5× |
| Q6_K | 41% | 3.17 | 68.5 | 1.7× |
| Q5_K_M | 36% | 2.84 | 73.0 | 1.8× |
| Q4_K_M | 31% | 2.53 | ~80 | 2.0× |
| Q3_K_M | 25% | 2.16 | ~80 | 1.9–2.0× |
| Q2_K | 20% | 1.83 | 91–99 | 2.2–2.4× |
Figure: `speed_vs_size.png`. Point: most of the speed-up arrives by Q4; below that, gains flatten.

## 4.5 Results — quality (task grader + KLD)
| Version | Notes quality | Q&A | Halluc. | KLD | Same top token | PPL |
|---|---|---|---|---|---|---|
| BF16 | 61% | 92% | 0% | 0 | 100% | 13.72 |
| Q8_0 | 60% | 92% | 0% | 0.002 | 97.9% | 13.74 |
| Q6_K | 57% | 92% | 0% | 0.010 | 94.5% | 13.85 |
| Q5_K_M | 52% | 88% | 0% | 0.035 | 89.9% | 14.15 |
| Q4_K_M plain | 48% | 88% | 0% | 0.091 | 83.5% | 14.87 |
| Q4_K_M calibrated | 61% | 88% | 0% | 0.036 | 90.7% | 13.69 |
| Q4_K_M unsloth | 58% | 92% | 0% | 0.035 | 90.7% | 13.73 |
| Q3_K_M plain | 54% | 88% | 17% | 0.280 | 73.6% | 18.36 |
| Q3_K_M calibrated | 52% | 84% | 0% | 0.113 | 82.0% | 14.81 |
| Q2_K plain | 25% | 24% | 0% | 1.241 | 50.6% | 42.47 |
| Q2_K calibrated | 62% | 92% | 17% | 0.320 | 72.1% | 17.34 |
Figures: `quality_vs_size.png`, `kld_vs_bpw.png` (main), `field_heatmap.png`

Points to make:
- **Q8/Q6 are near-lossless** (KLD ≤ 0.01, task scores within noise) at 1.5–1.7× speed and ≤ 53% size.
- **Calibration cuts drift 2.5–4× at equal size** (Q4 0.091→0.036, Q3 0.280→0.113, Q2 1.24→0.32) —
  worth roughly one extra bit per weight (calibrated Q4 ≈ plain Q5).
- **unsloth's Q4_K_M ≈ our calibrated Q4_K_M** (KLD 0.035 vs 0.036, identical 90.7% top-token) → community
  files are calibrated; a plain self-made Q4 is measurably worse (task −13 pts, mostly summaries breaking the
  2-sentence rule: 24% of notes failed even after retry).
- **Plain Q2_K collapses:** half its top tokens differ from BF16, PPL ×3; on Q&A it refused *every* answerable
  question when valid (a degenerate "safe" model), 32% of its Q&A outputs invalid.
- **Small task benchmarks can hide degradation:** calibrated Q2_K matched BF16 on our 25-item tasks, but KLD
  (0.32) and same-top (72%) show real drift — and it produced the only low-bit hallucination besides plain Q3.
  Pair task scores with a distribution metric.
- Hallucination appears only at ≤ 4 bits per weight.

## 4.6 Recommendation
- **Q4_K_M calibrated (or a reputable calibrated download)** = the sweet spot: 31% size, 2× speed, task quality
  = BF16, KLD 0.036. **Q6_K** when near-zero drift matters. **Never uncalibrated ≤ 4 bits; avoid Q2 for anything
  important.**

## 4.7 Limitations
- One model (Granite 3B); larger models usually tolerate quantization better — don't generalise blindly.
- 25 items per track (4 pts = 1 item): trust large effects; KLD resolves the close calls.
- KLD / PPL text is our own 60 notes (~3.4k tokens): good for relative ranking, small for absolute PPL
  (calibrated Q4's 13.69 < BF16 13.72 is noise).
- 2 rounds per version; `-c 4096` differs from Phase 3's 8192 (compare speeds within Phase 4 only).
- unsloth's imatrix was computed for their pipeline; a matrix computed on domain notes might do better (or overfit).
