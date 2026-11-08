"""
Phase 3 - model comparison analysis.

    python harness/analyze_phase3.py results/raw/phase3_*.jsonl

Reads raw rows + their .meta.json (background memory samples) + results/raw/phase3_idle_vram.csv,
grades every row with grade.py, and writes results/summary/phase3_models/:
  summary.md / summary.csv     one row per model x enforcement mode
  per_field.csv                Track A field accuracy per model (where do models differ?)
  charts                       speed, memory, quality bars; quality-vs-speed scatter

Memory: footprint = VRAM after load (idle, before the first request) minus VRAM measured before the server
started; peak adds KV cache + compute buffers during generation. Medians across rounds.
Reproducibility: share of items whose temperature-0 output is identical across the 3 rounds, i.e. across
separate server restarts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade import grade_rows, load_gold  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["note_type", "tags", "actions_f1", "due_acc", "entities_f1"]


def load_runs(paths: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, metas = [], []
    for p in paths:
        p = Path(p)
        rows += [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]
        meta_path = p.parent / (p.stem + ".meta.json")
        if meta_path.exists():
            m = json.loads(meta_path.read_text(encoding="utf-8"))
            eff = m.get("effective", {})
            metas.append({"run_id": m["run_id"], "model": m["config"].get("model_label"),
                          "enforcement": eff.get("enforcement"), "started": m.get("started"),
                          **(m.get("sysmon") or {})})
    return pd.DataFrame(rows), pd.DataFrame(metas)


def memory_table(metas: pd.DataFrame, idle_csv: Path) -> pd.DataFrame:
    if metas.empty or "vram_start_mib" not in metas:
        return pd.DataFrame(columns=["model"])
    idle = pd.read_csv(idle_csv) if idle_csv.exists() else pd.DataFrame(columns=["label", "vram_idle_mib"])
    idle_med = idle.groupby("label")["vram_idle_mib"].median()
    m = metas.groupby("model").agg(vram_loaded_mib=("vram_start_mib", "median"),
                                   vram_peak_mib=("vram_peak_mib", "max"),
                                   ram_peak_mib=("ram_peak_mib", "max"),
                                   gpu_temp_max_c=("gpu_temp_max_c", "max")).reset_index()
    m["vram_idle_mib"] = m["model"].map(idle_med)
    m["model_vram_gb"] = (m["vram_loaded_mib"] - m["vram_idle_mib"].fillna(0)) / 1024
    m["peak_vram_gb"] = (m["vram_peak_mib"] - m["vram_idle_mib"].fillna(0)) / 1024
    return m


def speed_quality_table(raw: pd.DataFrame, graded: pd.DataFrame) -> pd.DataFrame:
    raw = raw[~raw["is_warmup"]]
    out = []
    for (model, mode), g in graded.groupby(["model", "enforcement"]):
        r = raw[(raw["model"] == model) & (raw["enforcement"] == mode)]
        a, b = g[g.track == "A"], g[g.track == "B"]
        ra, rb = r[r.track == "A"], r[r.track == "B"]
        unans = b[~b["expected_answerable"].astype(bool)]
        out.append({
            "model": model, "enforcement": mode,
            "decode_tps": r["decode_tps"].median(),
            "prefill_tps": r["prefill_tps"].median(),
            "ttft_a_ms": ra["ttft_ms"].median(), "ttft_b_ms": rb["ttft_ms"].median(),
            "latency_a_ms": ra["total_latency_ms"].median(), "latency_b_ms": rb["total_latency_ms"].median(),
            "latency_a_p95_ms": ra["total_latency_ms"].quantile(0.95),
            "input_tokens_a": ra["prompt_n"].median(), "input_tokens_b": rb["prompt_n"].median(),
            "output_tokens_a": ra["predicted_n"].median(),
            "a_first_try_valid": (a["status"] == "ok_first").mean(),
            "a_final_valid": a["valid"].mean(),
            "a_quality": a["field_score"].mean(),
            "b_first_try_valid": (b["status"] == "ok_first").mean(),
            "b_quality": b["qa_score"].mean(),
            "b_hallucination": unans["hallucinated"].astype(bool).mean() if len(unans) else float("nan"),
            "invented_tasks": a["invented_tasks"].astype(bool).mean(),
            "reproducible": reproducibility(g),
            "rounds": g["repeat"].nunique(),
        })
    return pd.DataFrame(out)


def reproducibility(g: pd.DataFrame) -> float:
    fj = g["final_json"].where(g["final_json"].map(lambda x: isinstance(x, str)), "FAILED")
    per_item = g.assign(fj=fj).groupby(["track", "item_id"])["fj"].nunique()
    n = g.groupby(["track", "item_id"]).size()
    per_item = per_item[n > 1]
    return float((per_item == 1).mean()) if len(per_item) else float("nan")


def pct(x) -> str:
    return "-" if pd.isna(x) else f"{x:.0%}"


def num(x, d=0) -> str:
    return "-" if pd.isna(x) else f"{x:,.{d}f}"


def markdown(t: pd.DataFrame) -> list[str]:
    md = ["## Speed and memory (json_schema mode)", "",
          "| Model | Quant | Model VRAM (GB) | Peak VRAM (GB) | Server RAM peak (GB) | Decode tok/s | Prefill tok/s "
          "| TTFT A / B (ms) | Latency A / B (ms) | Input tokens A / B |", "|" + "---|" * 10]
    s = t[t.enforcement == "json_schema"]
    for _, r in s.iterrows():
        ram_gb = r.ram_peak_mib / 1024 if pd.notna(r.get("ram_peak_mib")) else float("nan")
        md.append(f"| {r.model} | {r.quant} | {num(r.model_vram_gb, 2)} | {num(r.peak_vram_gb, 2)} | {num(ram_gb, 2)} | "
                  f"{num(r.decode_tps, 1)} | {num(r.prefill_tps)} | {num(r.ttft_a_ms)} / {num(r.ttft_b_ms)} | "
                  f"{num(r.latency_a_ms)} / {num(r.latency_b_ms)} | {num(r.input_tokens_a)} / {num(r.input_tokens_b)} |")
    md += ["", "Model VRAM = GPU memory after load minus GPU memory before the server started. Server RAM = peak resident "
           "memory of llama-server (includes memory-mapped model pages and any weights llama.cpp keeps on the CPU, "
           "e.g. Gemma's per-layer embedding tables). Compare both, not VRAM alone.",
           "", "## Structure and quality", "",
           "| Model | Mode | A first-try valid | A final valid | A quality | Invented tasks | B quality "
           "| B hallucination | Reproducible across restarts |", "|" + "---|" * 9]
    for _, r in t.sort_values(["enforcement", "model"]).iterrows():
        md.append(f"| {r.model} | {r.enforcement} | {pct(r.a_first_try_valid)} | {pct(r.a_final_valid)} | "
                  f"{pct(r.a_quality)} | {pct(r.invented_tasks)} | {pct(r.b_quality)} | {pct(r.b_hallucination)} | "
                  f"{pct(r.reproducible)} |")
    md += ["", "## Efficiency (json_schema mode)", "",
           "| Model | A quality per GB VRAM | A quality per second (Track A latency) |", "|---|---|---|"]
    for _, r in s.iterrows():
        md.append(f"| {r.model} | {num(r.a_quality * 100 / r.model_vram_gb, 1) if r.model_vram_gb else '-'} pts/GB | "
                  f"{num(r.a_quality * 100 / (r.latency_a_ms / 1000), 1)} pts/s |")
    return md


def charts(t: pd.DataFrame, per_field: pd.DataFrame, out: Path) -> None:
    s = t[t.enforcement == "json_schema"].sort_values("model")
    colors = ["#2a6fdb", "#e07b39", "#2e9e5b", "#8e5cc2", "#c94f6d"][: len(s)]

    fig, axes = plt.subplots(1, 4, figsize=(15, 3.8))
    for ax, (col, title, scale) in zip(axes, [("decode_tps", "Decode tok/s", 1), ("model_vram_gb", "Model VRAM (GB)", 1),
                                              ("a_quality", "Track A quality (%)", 100), ("b_quality", "Track B quality (%)", 100)]):
        ax.bar(s["model"], s[col] * scale, color=colors)
        ax.set_title(title); ax.tick_params(axis="x", rotation=30, labelsize=7); ax.grid(alpha=0.3, axis="y")
    fig.suptitle("Model comparison (json_schema, temperature 0)")
    fig.tight_layout(); fig.savefig(out / "model_comparison_bars.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for (_, r), c in zip(s.iterrows(), colors):
        size = 300 * (r["model_vram_gb"] if pd.notna(r["model_vram_gb"]) else 2)
        ax.scatter(r["latency_a_ms"] / 1000, r["a_quality"] * 100, s=size, color=c, alpha=0.6)
        ax.annotate(r["model"], (r["latency_a_ms"] / 1000, r["a_quality"] * 100), fontsize=8, ha="center", va="bottom")
    ax.set(xlabel="Track A median latency (s)  - lower is better", ylabel="Track A quality (%)",
           title="Quality vs speed (bubble size = VRAM)")
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out / "quality_vs_latency.png", dpi=150); plt.close(fig)

    if not per_field.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        pf = per_field.set_index("model")[FIELDS] * 100
        pf.T.plot(kind="bar", ax=ax, color=colors[: len(pf)])
        ax.set(ylabel="% (json_schema)", title="Track A accuracy by field"); ax.grid(alpha=0.3, axis="y")
        ax.tick_params(axis="x", rotation=0)
        fig.tight_layout(); fig.savefig(out / "track_a_fields.png", dpi=150); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--corpus", default=str(ROOT / "second_brain_corpus" / "build"))
    ap.add_argument("--idle-csv", default=str(ROOT / "results" / "raw" / "phase3_idle_vram.csv"))
    args = ap.parse_args()

    raw, metas = load_runs(args.paths)
    gold_a, meta_a, gold_b = load_gold(Path(args.corpus))
    graded = pd.DataFrame(grade_rows(raw.to_dict("records"), gold_a, meta_a, gold_b))
    # A smoke test (--limit) may contain only one track: make sure every column exists.
    for col, default in [("expected_answerable", True), ("hallucinated", False), ("qa_score", float("nan")),
                         ("field_score", float("nan")), ("invented_tasks", False)] + [(f, float("nan")) for f in FIELDS]:
        if col not in graded:
            graded[col] = default

    t = speed_quality_table(raw, graded)
    quant = raw.groupby("model")["quant"].first()
    t["quant"] = t["model"].map(quant)
    t = t.merge(memory_table(metas, Path(args.idle_csv)), on="model", how="left")
    a = graded[(graded.track == "A") & (graded.enforcement == "json_schema")]
    per_field = a.groupby("model")[FIELDS].mean().reset_index()

    out = ROOT / "results" / "summary" / "phase3_models"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "summary.csv", index=False)
    per_field.to_csv(out / "per_field.csv", index=False)
    graded.drop(columns=["final_json"]).to_json(out / "graded_rows.jsonl", orient="records", lines=True)
    charts(t, per_field, out)

    md = [f"# Phase 3 - model comparison", "",
          f"Runs: {raw['run_id'].nunique()} | graded rows: {len(graded)} | models: {', '.join(sorted(t.model.unique()))} | "
          f"temperature 0, one retry, llama.cpp b11954, -np 1, -c 8192", ""] + markdown(t) + \
         ["", "## Track A accuracy by field (json_schema)", "", "```",
          (per_field.set_index("model") * 100).round(0).to_string(), "```", "", "Charts: *.png in this folder", ""]
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
