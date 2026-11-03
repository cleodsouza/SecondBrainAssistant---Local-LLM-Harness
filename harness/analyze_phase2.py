"""
Phase 2 analysis: structure, reliability and determinism across enforcement modes and temperatures.

    python harness/analyze_phase2.py --label enforcement results/raw/phase2_*.jsonl

Writes results/summary/phase2_<label>/ : summary.md, summary.csv, error_examples.md, charts.

Per (enforcement, temperature, track) it reports
  first_try_valid  - share of items valid on attempt 1                 (how good is the raw output?)
  needed_retry     - share that failed attempt 1
  rescued          - of those, share fixed by the one retry            (is the retry worth it?)
  final_valid      - share valid after the retry                       (what the app actually sees)
  err_*            - attempt-1 failures by type: empty / not_json / schema / context
  decode_tps       - median decode speed on attempt 1                  (grammar cost)
  latency          - median attempt-1 latency and median / p95 total latency including retries
  identical_runs   - share of items whose final output is identical across all repeats (determinism)
Quality (is the content *correct*?) is added by grade.py in step 2.4.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KEYS = ["enforcement", "temperature", "track"]
MODE_ORDER = ["prompt_only", "json_object", "json_schema"]
MODE_COLORS = {"prompt_only": "#e07b39", "json_object": "#2a6fdb", "json_schema": "#2e9e5b"}
ERR_TYPES = ["empty", "not_json", "schema", "context"]


def load(paths: list[str]) -> pd.DataFrame:
    rows = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            rows += [json.loads(line) for line in f if line.strip()]
    df = pd.DataFrame(rows)
    if "status" not in df:
        raise SystemExit("These files have no 'status' column - they are Phase 1 runs. Use analyze_phase1.py.")
    df = df[~df["is_warmup"]].copy()
    df["temperature"] = df["temperature"].astype(float)
    df["final_json"] = df["final_output"].map(lambda o: json.dumps(o, sort_keys=True) if o else None)
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for key, g in df.groupby(KEYS):
        n = len(g)
        failed_first = g["status"] != "ok_first"
        row = dict(zip(KEYS, key))
        row.update({
            "n": n,
            "first_try_valid": (g["status"] == "ok_first").mean(),
            "needed_retry": failed_first.mean(),
            "rescued": (g["status"] == "ok_retry").sum() / failed_first.sum() if failed_first.any() else None,
            "final_valid": (g["status"] != "failed").mean(),
            **{f"err_{t}": int((g["first_error_type"] == t).sum()) for t in ERR_TYPES},
            "decode_tps": g["decode_tps"].median(),
            "latency_attempt1_ms": g["latency_ms"].median(),
            "latency_total_ms": g["total_latency_ms"].median(),
            "latency_total_p95_ms": g["total_latency_ms"].quantile(0.95),
            "output_tokens": g["predicted_n"].median(),
            "identical_runs": identical_share(g),
        })
        out.append(row)
    t = pd.DataFrame(out)
    t["enforcement"] = pd.Categorical(t["enforcement"], MODE_ORDER, ordered=True)
    return t.sort_values(KEYS).reset_index(drop=True)


def identical_share(g: pd.DataFrame) -> float | None:
    """Share of items whose final output is byte-identical across every repeat (failed counts as a value)."""
    per_item = g.groupby("item_id")["final_json"].agg(lambda s: s.fillna("FAILED").nunique() == 1)
    counts = g.groupby("item_id").size()
    per_item = per_item[counts > 1]
    return per_item.mean() if len(per_item) else None


def pct(x) -> str:
    return "-" if x is None or pd.isna(x) else f"{x:.0%}"


def markdown(t: pd.DataFrame) -> str:
    head = ("| Enforcement | Temp | Track | n | First-try valid | Needed retry | Rescued | Final valid "
            "| Attempt-1 errors (empty/not_json/schema/context) | Decode tok/s | Latency med (ms) "
            "| Total med / p95 (ms) | Identical across repeats |")
    lines = [head, "|" + "---|" * 13]
    for _, r in t.iterrows():
        errs = "/".join(str(r[f"err_{e}"]) for e in ERR_TYPES)
        lines.append(
            f"| {r.enforcement} | {r.temperature:.1f} | {r.track} | {r.n} | {pct(r.first_try_valid)} | "
            f"{pct(r.needed_retry)} | {pct(r.rescued)} | {pct(r.final_valid)} | {errs} | {r.decode_tps:.1f} | "
            f"{r.latency_attempt1_ms:.0f} | {r.latency_total_ms:.0f} / {r.latency_total_p95_ms:.0f} | "
            f"{pct(r.identical_runs)} |")
    return "\n".join(lines)


def error_examples(df: pd.DataFrame, per_setting: int = 3) -> str:
    """Most common attempt-1 error lines per setting, plus a few raw outputs - for error analysis."""
    md = ["# Attempt-1 error examples", ""]
    bad = df[df["status"] != "ok_first"]
    if bad.empty:
        return "# Attempt-1 error examples\n\nNo attempt-1 failures in these runs.\n"
    for key, g in bad.groupby(KEYS):
        md.append(f"## {key[0]} / temp {key[1]:.1f} / Track {key[2]}  ({len(g)} failures)")
        lines = Counter(line.split(" [got")[0] for e in g["first_error"].dropna() for line in e.splitlines())
        for line, c in lines.most_common(6):
            md.append(f"- {c} x `{line[:140]}`")
        for _, r in g.head(per_setting).iterrows():
            md.append(f"\n<details><summary>{r['item_id']} r{r['repeat']} - {r['status']}</summary>\n")
            md.append("```\n" + (r.output_text or "")[:800] + "\n```\n</details>")
        md.append("")
    return "\n".join(md)


def charts(t: pd.DataFrame, out: Path) -> None:
    temps = sorted(t["temperature"].unique())

    # 1. First-try validity vs temperature, per track
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, track in zip(axes, ["A", "B"]):
        for mode in MODE_ORDER:
            s = t[(t.track == track) & (t.enforcement == mode)].sort_values("temperature")
            if len(s):
                ax.plot(s.temperature, s.first_try_valid * 100, "o-", label=mode, color=MODE_COLORS[mode])
        ax.set(title=f"Track {track}", xlabel="Temperature", xticks=temps)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Valid on first try (%)")
    axes[0].legend()
    fig.suptitle("Schema-valid output on the first attempt")
    fig.tight_layout(); fig.savefig(out / "first_try_valid_vs_temperature.png", dpi=150); plt.close(fig)

    # 2. Outcome breakdown (stacked) per setting
    t2 = t.copy()
    t2["label"] = t2.apply(lambda r: f"{r.enforcement}\nT={r.temperature:.1f} {r.track}", axis=1)
    fig, ax = plt.subplots(figsize=(max(8, len(t2) * 0.8), 4.5))
    ok1 = t2.first_try_valid * 100
    okr = (t2.final_valid - t2.first_try_valid) * 100
    fail = (1 - t2.final_valid) * 100
    ax.bar(t2.label, ok1, color="#2e9e5b", label="valid first try")
    ax.bar(t2.label, okr, bottom=ok1, color="#f2b134", label="fixed by retry")
    ax.bar(t2.label, fail, bottom=ok1 + okr, color="#d64545", label="failed")
    ax.set(ylabel="% of items", title="Outcome per setting", ylim=(0, 100))
    ax.tick_params(axis="x", labelsize=7)
    ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(out / "outcomes_stacked.png", dpi=150); plt.close(fig)

    # 3. Cost of enforcement: decode speed and latency per mode (all temps pooled per track)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    agg = t.groupby(["enforcement", "track"], observed=True)[["decode_tps", "latency_total_ms"]].median().reset_index()
    for ax, col, label in zip(axes, ["decode_tps", "latency_total_ms"], ["Decode tok/s (median)", "Total latency ms (median)"]):
        for i, track in enumerate(["A", "B"]):
            s = agg[agg.track == track]
            xs = [MODE_ORDER.index(m) + i * 0.38 for m in s.enforcement]
            ax.bar(xs, s[col], width=0.36, label=f"Track {track}",
                   color=["#2a6fdb", "#e07b39"][i])
        ax.set_xticks([x + 0.19 for x in range(3)], MODE_ORDER)
        ax.set(title=label); ax.grid(alpha=0.3, axis="y")
    axes[0].legend()
    fig.suptitle("Cost of enforcement")
    fig.tight_layout(); fig.savefig(out / "enforcement_cost.png", dpi=150); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--label", default="run", help="output folder suffix, e.g. enforcement / temperature")
    args = ap.parse_args()

    df = load(args.paths)
    t = summarise(df)
    out = ROOT / "results" / "summary" / f"phase2_{args.label}"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "summary.csv", index=False)
    charts(t, out)
    (out / "error_examples.md").write_text(error_examples(df), encoding="utf-8")

    md = [f"# Phase 2 summary - {args.label}", "",
          f"Runs: {df['run_id'].nunique()}  |  items analysed: {len(df)} (warm-up excluded)  |  "
          f"model: {df['model'].iloc[0]} {df['quant'].iloc[0]}  |  max_retries: {df['max_retries'].iloc[0]}", "",
          markdown(t), "",
          "Attempt-1 error examples: error_examples.md  |  charts: *.png", ""]
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
