"""
Parse llama-perplexity logs (perplexity + KL-divergence mode) into one CSV row per model.

    python harness/parse_kld.py results/kld_logs results/raw/phase4_kld.csv

Patterns are deliberately loose: llama.cpp's exact wording shifts between builds. Any value not found is left
empty and the raw log stays in results/kld_logs for inspection.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

PATTERNS = {
    "ppl": [r"Mean PPL\(Q\)\s*:\s*([\d.]+)", r"Final estimate: PPL = ([\d.]+)"],
    "ppl_base": [r"Mean PPL\(base\)\s*:\s*([\d.]+)"],
    "kld_mean": [r"Mean\s+KLD\s*:\s*([-\d.eE]+)"],
    "kld_99": [r"99\.0%\s+KLD\s*:\s*([-\d.eE]+)"],
    "kld_max": [r"Maximum\s+KLD\s*:\s*([-\d.eE]+)"],
    "same_top_p": [r"Same top p\s*:\s*([\d.]+)"],
    "rms_dp": [r"RMS Δp\s*:\s*([\d.]+)", r"RMS dp\s*:\s*([\d.]+)"],
}


def parse(text: str) -> dict:
    out = {}
    for key, pats in PATTERNS.items():
        out[key] = ""
        for pat in pats:
            matches = re.findall(pat, text)
            if matches:
                out[key] = matches[-1]          # last occurrence = final estimate
                break
    return out


def main() -> None:
    logs, out_csv = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for log in sorted(logs.glob("*.log")):
        r = {"label": log.stem, **parse(log.read_text(encoding="utf-8", errors="replace"))}
        if r["label"].endswith("BF16"):
            r["kld_mean"], r["same_top_p"] = "0", "100"
        rows.append(r)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["label", *PATTERNS])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['label']:<26} PPL={r['ppl'] or '?':>8}  KLD={r['kld_mean'] or '?':>10}  same-top={r['same_top_p'] or '?'}")
    missing = [r["label"] for r in rows if not r["ppl"]]
    if missing:
        print(f"WARNING: no perplexity found in logs for {missing} - check results/kld_logs/")
    print(f"wrote {out_csv}")


if __name__ == "__main__":
    main()
