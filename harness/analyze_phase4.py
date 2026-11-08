"""
Phase 4 - quantization analysis: speed / memory / quality trade-off for one model at many precisions.

    python harness/analyze_phase4.py results/raw/phase4_*.jsonl

Reuses the Phase 3 machinery (grading, memory, speed) and adds, per version:
  file size, bits per weight (bpw = file bits / parameter count, parameters = BF16 bytes / 2),
  change vs the BF16 original, KL divergence + same-top-token + perplexity (results/raw/phase4_kld.csv,
  from run_phase4_kld.sh - optional), plain vs imatrix at equal bit width.
Writes results/summary/phase4_quant/: summary.md, summary.csv, per_field.csv, graded_rows.jsonl, charts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_phase3 import FIELDS, load_runs, memory_table, speed_quality_table  # noqa: E402
from grade import grade_rows, load_gold  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def model_table(cfg_path: Path) -> pd.DataFrame:
    ms = yaml.safe_load(open(cfg_path, encoding="utf-8"))["models"]
    df = pd.DataFrame(ms).rename(columns={"label": "model"})
    df["order"] = range(len(df))
    df["file_bytes"] = df["path"].map(lambda p: os.path.getsize(p) if os.path.exists(p) else float("nan"))
    df["file_gb"] = df["file_bytes"] / 1e9
    bf16 = df.loc[df["quant"] == "BF16", "file_bytes"]
    n_params = bf16.iloc[0] / 2 if len(bf16) and pd.notna(bf16.iloc[0]) else float("nan")
    df["bpw"] = df["file_bytes"] * 8 / n_params
    df["imatrix"] = df["imatrix"].astype(str)
    return df[["model", "quant", "imatrix", "source", "file_gb", "bpw", "order"]]


def pct(x) -> str:
    return "-" if pd.isna(x) else f"{x:.0%}"


def num(x, d=0) -> str:
    return "-" if pd.isna(x) else f"{x:,.{d}f}"


def signed(x, d=0, unit="") -> str:
    return "-" if pd.isna(x) else f"{x:+.{d}f}{unit}"


def charts(t: pd.DataFrame, per_field: pd.DataFrame, out: Path) -> None:
    def style(r):
        if r.source == "original":
            return dict(marker="*", s=220, color="#111111")
        if r.source == "unsloth":
            return dict(marker="D", s=80, color="#8e5cc2")
        return dict(marker="s" if r.imatrix == "True" else "o", s=70,
                    color="#2e9e5b" if r.imatrix == "True" else "#2a6fdb")

    for ycol, ylabel, fname in [("a_quality", "Track A quality (%)", "quality_vs_size.png"),
                                ("b_quality", "Track B quality (%)", "qa_quality_vs_size.png"),
                                ("decode_tps", "Decode tokens/s", "speed_vs_size.png")]:
        fig, ax = plt.subplots(figsize=(7.5, 4.8))
        scale = 1 if ycol == "decode_tps" else 100
        plain = t[(t.source == "ours") & (t.imatrix == "False")].sort_values("file_gb")
        ax.plot(plain.file_gb, plain[ycol] * scale, "-", color="#2a6fdb", alpha=0.4)
        for _, r in t.iterrows():
            ax.scatter(r.file_gb, r[ycol] * scale, zorder=3, **style(r))
            ax.annotate(r.quant + ("*" if r.imatrix == "True" else "") + (" (u)" if r.source == "unsloth" else ""),
                        (r.file_gb, r[ycol] * scale), fontsize=7, xytext=(4, 4), textcoords="offset points")
        ax.set(xlabel="Model file size (GB)", ylabel=ylabel,
               title=f"{ylabel} vs size  (circle = plain, square = imatrix, star = BF16, diamond = unsloth)")
        ax.title.set_fontsize(9)
        ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(out / fname, dpi=150); plt.close(fig)

    if t["kld_mean"].notna().any():
        k = t[t.quant != "BF16"].dropna(subset=["kld_mean"]).sort_values("bpw")
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for _, r in k.iterrows():
            ax.scatter(r.bpw, r.kld_mean, zorder=3, **style(r))
            ax.annotate(r.quant + ("*" if r.imatrix == "True" else ""), (r.bpw, r.kld_mean), fontsize=7,
                        xytext=(4, 4), textcoords="offset points")
        ax.set_yscale("log")
        ax.set(xlabel="Bits per weight", ylabel="Mean KL divergence vs BF16 (log)",
               title="How far each version's predictions drift from the original")
        ax.grid(alpha=0.3, which="both")
        fig.tight_layout(); fig.savefig(out / "kld_vs_bpw.png", dpi=150); plt.close(fig)

    if not per_field.empty:
        pf = per_field.set_index("model")[FIELDS] * 100
        fig, ax = plt.subplots(figsize=(7.5, 0.45 * len(pf) + 1.5))
        im = ax.imshow(pf.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(FIELDS)), FIELDS, fontsize=8)
        ax.set_yticks(range(len(pf)), pf.index, fontsize=8)
        for i in range(pf.shape[0]):
            for j in range(pf.shape[1]):
                ax.text(j, i, f"{pf.values[i, j]:.0f}", ha="center", va="center", fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.03)
        ax.set_title("Track A accuracy by field - which abilities degrade first")
        fig.tight_layout(); fig.savefig(out / "field_heatmap.png", dpi=150); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--models", default=str(ROOT / "configs" / "phase4_models.yaml"))
    ap.add_argument("--kld", default=str(ROOT / "results" / "raw" / "phase4_kld.csv"))
    ap.add_argument("--idle-csv", default=str(ROOT / "results" / "raw" / "phase4_idle_vram.csv"))
    ap.add_argument("--corpus", default=str(ROOT / "second_brain_corpus" / "build"))
    args = ap.parse_args()

    raw, metas = load_runs(args.paths)
    gold_a, meta_a, gold_b = load_gold(Path(args.corpus))
    graded = pd.DataFrame(grade_rows(raw.to_dict("records"), gold_a, meta_a, gold_b))
    for col, default in [("expected_answerable", True), ("hallucinated", False), ("qa_score", float("nan")),
                         ("field_score", float("nan")), ("invented_tasks", False)] + [(f, float("nan")) for f in FIELDS]:
        if col not in graded:
            graded[col] = default

    t = speed_quality_table(raw, graded)
    t = t[t.enforcement == "json_schema"].drop(columns=["enforcement"])
    t = t.merge(memory_table(metas, Path(args.idle_csv)), on="model", how="left")
    t = t.merge(model_table(Path(args.models)), on="model", how="left")
    if "sm_clock_busy_median_mhz" in metas:
        clk = metas.groupby("model")["sm_clock_busy_median_mhz"].median().rename("gpu_clock_mhz")
        t = t.merge(clk.reset_index(), on="model", how="left")
    else:
        t["gpu_clock_mhz"] = float("nan")
    kld_path = Path(args.kld)
    if kld_path.exists():
        k = pd.read_csv(kld_path).rename(columns={"label": "model"})
        t = t.merge(k, on="model", how="left")
    for c in ["kld_mean", "same_top_p", "ppl"]:
        if c not in t:
            t[c] = float("nan")
        t[c] = pd.to_numeric(t[c], errors="coerce")
    t = t.sort_values("order").reset_index(drop=True)

    base = t[t.quant == "BF16"]
    if len(base):
        b = base.iloc[0]
        t["d_quality_pts"] = (t["a_quality"] - b["a_quality"]) * 100
        t["d_qa_pts"] = (t["b_quality"] - b["b_quality"]) * 100
        t["speedup"] = t["decode_tps"] / b["decode_tps"]
        t["size_vs_bf16"] = t["file_gb"] / b["file_gb"]

    a = graded[(graded.track == "A")]
    per_field = a.groupby("model")[FIELDS].mean().reindex(t["model"]).reset_index()

    out = ROOT / "results" / "summary" / "phase4_quant"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "summary.csv", index=False)
    per_field.to_csv(out / "per_field.csv", index=False)
    graded.drop(columns=["final_json"]).to_json(out / "graded_rows.jsonl", orient="records", lines=True)
    charts(t, per_field, out)

    md = ["# Phase 4 - quantization study (Granite 4.1 3B)", "",
          f"Runs: {raw['run_id'].nunique()} | graded rows: {len(graded)} | schema mode, temperature 0, one retry, "
          f"llama.cpp b11954, -np 1, -c 4096. * = imatrix-calibrated, (u) = unsloth's file.", "",
          "| Version | Size (GB) | Bits/weight | Size vs BF16 | VRAM (GB) | Decode tok/s | Speed-up | Latency A / B (ms) "
          "| A first-try valid | A quality | Δ vs BF16 | B quality | Δ vs BF16 | Halluc. | KLD | Same top token | PPL |",
          "|" + "---|" * 17]
    for _, r in t.iterrows():
        name = r.quant + ("*" if r.imatrix == "True" else "") + (" (u)" if r.source == "unsloth" else "")
        md.append(
            f"| {name} | {num(r.file_gb, 2)} | {num(r.bpw, 2)} | {pct(r.get('size_vs_bf16'))} | {num(r.model_vram_gb, 2)} | "
            f"{num(r.decode_tps, 1)} | {num(r.get('speedup'), 2)}x | {num(r.latency_a_ms)} / {num(r.latency_b_ms)} | "
            f"{pct(r.a_first_try_valid)} | {pct(r.a_quality)} | {signed(r.get('d_quality_pts'), 0, ' pts')} | "
            f"{pct(r.b_quality)} | {signed(r.get('d_qa_pts'), 0, ' pts')} | {pct(r.b_hallucination)} | "
            f"{num(r.kld_mean, 4)} | {num(r.same_top_p, 1)}{'%' if pd.notna(r.same_top_p) else ''} | {num(r.ppl, 2)} |")
    # A GPU that is ~97% busy at an idle-level clock is waiting on memory - on Windows that means the model spilled
    # out of VRAM into system RAM, and its speed numbers are not comparable (seen with BF16 at -c 8192).
    slow = t[(t["gpu_clock_mhz"] < 0.5 * t["gpu_clock_mhz"].median())]
    if len(slow):
        md += ["", "**WARNING - possible VRAM spill:** GPU clock far below the other versions for "
               + ", ".join(f"{m} ({c:.0f} MHz)" for m, c in zip(slow.model, slow.gpu_clock_mhz))
               + ". Their speed numbers are not comparable; free GPU memory or lower the context and re-run."]
    md += ["", "## Track A accuracy by field", "", "```",
           (per_field.set_index("model") * 100).round(0).to_string(), "```", "",
           "Charts: quality_vs_size.png, qa_quality_vs_size.png, speed_vs_size.png, kld_vs_bpw.png, field_heatmap.png", ""]
    if not kld_path.exists():
        md.insert(3, "_KL divergence not yet available - run `bash run_phase4_kld.sh`, then re-run this analysis._\n")
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
