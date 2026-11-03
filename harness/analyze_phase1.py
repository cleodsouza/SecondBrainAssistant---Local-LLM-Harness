"""
Phase 1 analysis: latency / throughput statistics and charts from raw runner output.

    python harness/analyze_phase1.py results/raw/<run>.jsonl [results/raw/<run2>.jsonl ...] [--exclude-first N]

Writes results/summary/<run>/ : summary.csv, summary.md, and PNG charts.
With two or more runs it also writes a reproducibility table (median of each metric per run,
and the % difference from the first run) - the Phase 1 "done" check is < ~5% drift.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
METRICS = {
    "ttft_ms": "TTFT (ms)",
    "latency_ms": "Total latency (ms)",
    "prefill_tps": "Prefill (tok/s)",
    "decode_tps": "Decode (tok/s)",
    "prompt_n": "Input tokens",
    "predicted_n": "Output tokens",
}
TRACK_COLORS = {"A": "#2a6fdb", "B": "#e07b39"}


def load(paths: list[str]) -> pd.DataFrame:
    rows = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            rows += [json.loads(line) for line in f if line.strip()]
    df = pd.DataFrame(rows)
    df["json_parses"] = df["output_text"].map(_parses)
    return df


def _parses(text: str) -> bool:
    try:
        json.loads(text.strip())
        return True
    except Exception:
        return False


def stats_table(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    def p95(s): return s.quantile(0.95)
    agg = df.groupby(by)[list(METRICS)].agg(["mean", "median", p95, "std"])
    agg.columns = [f"{m}_{s}" for m, s in agg.columns]
    agg["n"] = df.groupby(by).size()
    agg["json_parse_rate"] = df.groupby(by)["json_parses"].mean()
    agg["hit_token_limit"] = df.groupby(by)["stop_type"].apply(lambda s: (s == "limit").mean())
    return agg.round(2)


def markdown_table(df: pd.DataFrame) -> str:
    lines = ["| Track | n | TTFT median (ms) | TTFT p95 (ms) | Prefill median (tok/s) | Decode median (tok/s) "
             "| Decode std | Latency median (ms) | Latency p95 (ms) | Input tok (median) | Output tok (median) "
             "| JSON parses |", "|" + "---|" * 12]
    for track, r in df.iterrows():
        lines.append(
            f"| {track} | {int(r['n'])} | {r['ttft_ms_median']:.0f} | {r['ttft_ms_p95']:.0f} | "
            f"{r['prefill_tps_median']:.0f} | {r['decode_tps_median']:.1f} | {r['decode_tps_std']:.1f} | "
            f"{r['latency_ms_median']:.0f} | {r['latency_ms_p95']:.0f} | {r['prompt_n_median']:.0f} | "
            f"{r['predicted_n_median']:.0f} | {r['json_parse_rate']:.0%} |")
    return "\n".join(lines)


def _md(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown()          # needs the optional 'tabulate' package
    except ImportError:
        return "```\n" + df.to_string() + "\n```"


def charts(df: pd.DataFrame, out: Path) -> None:
    # 1. TTFT vs input length - prefill cost scales with prompt tokens
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for tr, g in df.groupby("track"):
        ax.scatter(g["prompt_n"], g["ttft_ms"], s=14, alpha=0.6, label=f"Track {tr}", color=TRACK_COLORS.get(tr))
    ax.set(xlabel="Input tokens", ylabel="TTFT (ms)", title="Time to first token vs input length")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out / "ttft_vs_input_tokens.png", dpi=150); plt.close(fig)

    # 2. Decode speed over the run - flat = no thermal throttling (first run only, so seq is meaningful)
    df = df[df["run_id"] == df["run_id"].iloc[0]].sort_values("seq")
    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.plot(df["seq"], df["decode_tps"], ".", ms=4, alpha=0.6, color="#2a6fdb", label="decode tok/s")
    ax1.plot(df["seq"], df["decode_tps"].rolling(15, min_periods=1).median(), color="#123d7a", lw=1.5,
             label="rolling median")
    ax1.set(xlabel="Request # (run order)", ylabel="Decode (tok/s)", title="Decode throughput over the run")
    ax1.grid(alpha=0.3)
    if "gpu_temp_c" in df and df["gpu_temp_c"].notna().any():
        ax2 = ax1.twinx()
        ax2.plot(df["seq"], df["gpu_temp_c"], color="#e07b39", lw=1, alpha=0.8, label="GPU temp (°C)")
        ax2.set_ylabel("GPU temperature (°C)")
        h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, loc="lower left")
    else:
        ax1.legend(loc="lower left")
    fig.tight_layout(); fig.savefig(out / "decode_over_run.png", dpi=150); plt.close(fig)

    # 3. Latency distribution per track
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for tr, g in df.groupby("track"):
        ax.hist(g["latency_ms"] / 1000, bins=30, alpha=0.6, label=f"Track {tr}", color=TRACK_COLORS.get(tr))
    ax.set(xlabel="End-to-end latency (s)", ylabel="Requests", title="Latency distribution")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out / "latency_hist.png", dpi=150); plt.close(fig)

    # 4. Latency vs output tokens - shows latency is dominated by decode length
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for tr, g in df.groupby("track"):
        ax.scatter(g["predicted_n"], g["latency_ms"] / 1000, s=14, alpha=0.6, label=f"Track {tr}",
                   color=TRACK_COLORS.get(tr))
    ax.set(xlabel="Output tokens", ylabel="Latency (s)", title="Latency vs output length")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out / "latency_vs_output_tokens.png", dpi=150); plt.close(fig)


def main() -> None:
    args = sys.argv[1:]
    exclude_first = 0
    if "--exclude-first" in args:          # drop the first N requests of each run (GPU clock ramp-up)
        i = args.index("--exclude-first")
        exclude_first = int(args[i + 1])
        del args[i:i + 2]
    paths = args
    if not paths:
        sys.exit(__doc__)
    df_all = load(paths)
    errors = df_all["error"].notna().sum()
    df = df_all[(~df_all["is_warmup"]) & df_all["error"].isna() & (df_all["seq"] > exclude_first)].copy()

    run_name = Path(paths[0]).stem
    out = ROOT / "results" / "summary" / run_name
    out.mkdir(parents=True, exist_ok=True)

    by_track = stats_table(df, ["track"])
    overall = stats_table(df.assign(track="all"), ["track"])
    table = pd.concat([by_track, overall])
    table.to_csv(out / "summary.csv")
    charts(df, out)

    # temperature-0 determinism preview: identical output text across repeats?
    det = (df.groupby(["track", "item_id"])["output_text"].nunique() == 1).groupby("track").mean()

    md = [f"# Phase 1 summary - {run_name}", "",
          f"Runs: {', '.join(Path(p).stem for p in paths)}  ",
          f"Requests analysed: {len(df)} (excluded {int(df_all['is_warmup'].sum())} warm-up, {errors} errors"
          + (f", first {exclude_first} requests of each run" if exclude_first else "") + ")  ",
          f"Model: {df['model'].iloc[0]} {df['quant'].iloc[0]} - temperature {df['temperature'].iloc[0]}", "",
          markdown_table(table), "",
          "Identical output across repeats (determinism preview): "
          + ", ".join(f"Track {k}: {v:.0%}" for k, v in det.items()), ""]

    if len(paths) > 1:
        med = df.groupby("run_id")[["ttft_ms", "prefill_tps", "decode_tps", "latency_ms"]].median()
        drift = ((med / med.iloc[0] - 1) * 100).round(1)
        med.round(1).to_csv(out / "reproducibility_medians.csv")
        md += ["## Reproducibility (median per run, % vs first run)", "",
               _md(drift), ""]

    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\ncharts + tables in {out}")


if __name__ == "__main__":
    main()
