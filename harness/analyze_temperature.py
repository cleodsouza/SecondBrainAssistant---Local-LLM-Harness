"""
Phase 2.5 - temperature sweep analysis: how randomness affects structure, quality and consistency.

    python harness/analyze_temperature.py results/raw/phase2_*_t*.jsonl

Writes results/summary/phase2_temperature/ : summary.md, summary.csv, 4 charts, plus graded rows.

Per (enforcement, sampling_filters, temperature, track):
  first_try_valid / final_valid / retry_rate  - structure (from the runner's status)
  quality        - Track A field_score, Track B qa_score (from grade.py; failed outputs score 0)
  hallucination  - Track B: answered an unanswerable question
  identical      - share of items whose final output is byte-identical across all repeats
  agreement      - share of items where the KEY DECISION agrees across repeats:
                   Track A: same note_type AND same tag set AND same number of action items
                   Track B: same answerable flag AND same correctness
                   (catches meaningful disagreement while ignoring rewording of titles/summaries)
  latency        - median and p95 total latency incl. retries
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
KEYS = ["enforcement", "sampling_filters", "temperature", "track"]
COLORS = {"prompt_only": "#e07b39", "json_object": "#2a6fdb", "json_schema": "#2e9e5b"}


def decision_key(row: pd.Series) -> str:
    """The parts of an output that matter for agreement across repeats."""
    if not isinstance(row["final_json"], str):        # None / NaN = no valid output
        return "FAILED"
    out = json.loads(row["final_json"])
    if row["track"] == "A":
        return json.dumps([out.get("note_type"), sorted(out.get("tags", [])), len(out.get("action_items", []))])
    return json.dumps([out.get("answerable"), bool(row["answer_ok"])])


def agreement(g: pd.DataFrame, col: str) -> float:
    per_item = g.groupby("item_id")[col].nunique()
    counts = g.groupby("item_id").size()
    per_item = per_item[counts > 1]
    return float((per_item == 1).mean()) if len(per_item) else float("nan")


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(KEYS):
        is_a = key[-1] == "A"
        quality = g["field_score"] if is_a else g["qa_score"]
        r = dict(zip(KEYS, key))
        r.update({
            "n": len(g),
            "first_try_valid": (g["status"] == "ok_first").mean(),
            "retry_rate": (g["status"] != "ok_first").mean(),
            "final_valid": g["valid"].mean(),
            "quality": quality.mean(),
            "hallucination": (g.loc[~g["expected_answerable"].astype(bool), "hallucinated"].astype(bool).mean()
                              if not is_a else float("nan")),
            "identical": agreement(g.assign(fj=g["final_json"].fillna("FAILED")), "fj"),
            "agreement": agreement(g, "decision"),
            "latency_med_ms": g["total_latency_ms"].median(),
            "latency_p95_ms": g["total_latency_ms"].quantile(0.95),
        })
        rows.append(r)
    return pd.DataFrame(rows).sort_values(KEYS).reset_index(drop=True)


def fmt(v, kind="pct") -> str:
    if v is None or pd.isna(v):
        return "-"
    return f"{v:.0%}" if kind == "pct" else f"{v:,.0f}"


def markdown(t: pd.DataFrame) -> str:
    cols = ["Mode", "Filters", "Temp", "Track", "n", "First-try valid", "Final valid", "Quality",
            "Hallucination", "Identical", "Agreement", "Latency med / p95 (ms)"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in t.iterrows():
        lines.append(f"| {r.enforcement} | {r.sampling_filters} | {r.temperature:.1f} | {r.track} | {r.n} | "
                     f"{fmt(r.first_try_valid)} | {fmt(r.final_valid)} | {fmt(r.quality)} | {fmt(r.hallucination)} | "
                     f"{fmt(r.identical)} | {fmt(r.agreement)} | "
                     f"{fmt(r.latency_med_ms, 'n')} / {fmt(r.latency_p95_ms, 'n')} |")
    return "\n".join(lines)


def charts(t: pd.DataFrame, out: Path) -> None:
    main = t[t.sampling_filters == "on"]
    side = t[t.sampling_filters == "off"]
    panels = [("first_try_valid", "Valid on first try (%)"), ("quality", "Quality (%)"),
              ("agreement", "Same decision across repeats (%)"), ("latency_med_ms", "Median total latency (ms)")]
    for metric, label in panels:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=(metric != "latency_med_ms"))
        for ax, track in zip(axes, ["A", "B"]):
            for mode, g in main[main.track == track].groupby("enforcement"):
                g = g.sort_values("temperature")
                scale = 1 if metric == "latency_med_ms" else 100
                ax.plot(g.temperature, g[metric] * scale, "o-", color=COLORS.get(mode), label=mode)
                s = side[(side.track == track) & (side.enforcement == mode)]
                if len(s):
                    ax.plot(s.temperature, s[metric] * scale, "x", ms=10, mew=2, color=COLORS.get(mode),
                            label=f"{mode} (filters off)")
            ax.set(title=f"Track {track}", xlabel="Temperature")
            ax.grid(alpha=0.3)
        axes[0].set_ylabel(label)
        axes[0].legend(fontsize=8)
        fig.suptitle(label + " vs temperature")
        fig.tight_layout()
        fig.savefig(out / f"{metric}_vs_temperature.png", dpi=150)
        plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--label", default="temperature")
    ap.add_argument("--corpus", default=str(ROOT / "second_brain_corpus" / "build"))
    args = ap.parse_args()

    gold_a, meta_a, gold_b = load_gold(Path(args.corpus))
    graded = []
    for p in args.paths:
        rows = [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]
        graded += grade_rows(rows, gold_a, meta_a, gold_b)
    df = pd.DataFrame(graded)
    df["temperature"] = df["temperature"].astype(float)
    df["decision"] = df.apply(decision_key, axis=1)

    out = ROOT / "results" / "summary" / f"phase2_{args.label}"
    out.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["final_json"]).to_json(out / "graded_rows.jsonl", orient="records", lines=True)
    t = summarise(df)
    t.to_csv(out / "summary.csv", index=False)
    charts(t, out)

    seeds = sorted(df["seed"].dropna().unique().tolist())
    md = [f"# Phase 2.5 - temperature sweep ({args.label})", "",
          f"Runs: {df['run_id'].nunique()}  |  graded rows: {len(df)}  |  seeds used: {seeds}  |  "
          f"model: {df['model'].iloc[0]} {df['quant'].iloc[0]}", "",
          "Quality = Track A field_score / Track B qa_score (failed outputs score 0). "
          "Identical = same output text across repeats; Agreement = same key decision across repeats.", "",
          markdown(t), "", "Charts: *_vs_temperature.png", ""]
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
