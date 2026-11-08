"""
Benchmark runner for llama-server (llama.cpp).

    python harness/runner.py --config configs/phase1_pilot.yaml
    python harness/runner.py --config configs/phase2_base.yaml --enforcement json_schema --temperature 0.7

For every prompt x repeat it runs one *structured generation* (validate -> optional retry, see
structured.py) and writes ONE raw row to results/raw/<name>_<timestamp>.jsonl.
Rows are never edited; all analysis reads them.

Timing fields at the top level of a row always describe ATTEMPT 1, so they stay comparable with
Phase 1. Retry cost is recorded separately (retry_latency_ms, total_latency_ms).

What is measured per request
  client side : ttft_ms (request sent -> first streamed token), latency_ms (request sent -> stream end)
  server side : prompt_n / prompt_ms / prefill_tps  (prompt processing)
                predicted_n / predicted_ms / decode_tps (generation)
  GPU         : temperature, SM clock, power after each request (nvidia-smi, outside the timed region)

Fairness controls: cache_prompt=false (prefill is always measured from scratch), fixed sampling params
and seed, warm-up requests excluded, item order shuffled per repeat with a fixed seed.
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from enforcement import MODES, enforcement_params  # noqa: E402
from prompts import PROMPT_VERSION, track_a_messages, track_b_messages  # noqa: E402
from structured import generate_structured  # noqa: E402
from sysmon import SysMon  # noqa: E402
from validate import NoteAnswer, ProcessedNote  # noqa: E402

SCHEMAS = {"A": ProcessedNote, "B": NoteAnswer}

ROOT = Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------------------- data
def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_items(corpus_dir: Path, tracks: list[str], limit: int | None = None) -> list[dict]:
    """Returns [{track, item_id, messages, n_chunks}] for the requested tracks."""
    items: list[dict] = []
    if "A" in tracks:
        notes = {n["id"]: n for n in read_jsonl(corpus_dir / "notes.jsonl")}
        for a in read_jsonl(corpus_dir / "track_a.jsonl"):
            items.append({"track": "A", "item_id": a["id"], "n_chunks": None,
                          "messages": track_a_messages(notes[a["note_id"]])})
    if "B" in tracks:
        frozen = corpus_dir / "track_b_frozen.jsonl"
        if not frozen.exists():
            sys.exit(f"{frozen} not found - run second_brain_corpus/freeze_contexts.py first")
        for b in read_jsonl(frozen):
            items.append({"track": "B", "item_id": b["id"], "n_chunks": len(b["context_chunks"]),
                          "messages": track_b_messages(b)})
    if limit:
        items = items[:limit]
    return items


# ----------------------------------------------------------------------------- server
class LlamaServer:
    def __init__(self, base_url: str, timeout: float = 300):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.http = requests.Session()

    def wait_ready(self, max_wait: float = 120) -> None:
        t0 = time.time()
        warned = False
        while time.time() - t0 < max_wait:
            try:
                if self.http.get(f"{self.base}/health", timeout=5).status_code == 200:
                    return
            except requests.ConnectionError:
                if not warned:
                    print(f"Waiting for llama-server at {self.base} (start it in another window; "
                          f"giving up after {max_wait:.0f}s)...")
                    warned = True
            time.sleep(2)
        sys.exit(f"llama-server at {self.base} did not respond. In another Git Bash window, from "
                 f"D:\\SLM Project, run:  bash start_server.sh")

    def props(self) -> dict:
        try:
            return self.http.get(f"{self.base}/props", timeout=10).json()
        except Exception as e:  # props is informational only
            return {"error": str(e)}

    def apply_template(self, messages: list[dict]) -> str:
        r = self.http.post(f"{self.base}/apply-template", json={"messages": messages}, timeout=30)
        r.raise_for_status()
        return r.json()["prompt"]

    def stream_completion(self, prompt: str, params: dict) -> dict:
        """One streamed generation. Returns text, client timings and the server's timing block."""
        body = {**params, "prompt": prompt, "stream": True, "cache_prompt": False}
        pieces: list[str] = []
        final: dict = {}
        t_first = None
        t0 = time.perf_counter()
        with self.http.post(f"{self.base}/completion", json=body, stream=True, timeout=self.timeout) as r:
            r.raise_for_status()
            for raw in r.iter_lines(decode_unicode=False):
                if not raw or not raw.startswith(b"data:"):
                    continue
                payload = raw[5:].strip()
                if payload == b"[DONE]":
                    break
                chunk = json.loads(payload)
                text = chunk.get("content", "")
                if text and t_first is None:
                    t_first = time.perf_counter()
                pieces.append(text)
                if chunk.get("stop"):
                    final = chunk
                    break
        t_end = time.perf_counter()
        return {
            "text": "".join(pieces),
            "ttft_ms": (t_first - t0) * 1000 if t_first else None,
            "latency_ms": (t_end - t0) * 1000,
            "final": final,
        }


# ----------------------------------------------------------------------------- system info
def gpu_sample() -> dict:
    if not shutil.which("nvidia-smi"):
        return {}
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,clocks.sm,power.draw,memory.used",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5).stdout
        temp, clock, power, mem = [x.strip() for x in out.splitlines()[0].split(",")]
        return {"gpu_temp_c": float(temp), "gpu_sm_mhz": float(clock),
                "gpu_power_w": float(power), "gpu_mem_used_mib": float(mem)}
    except Exception:
        return {}


def gpu_info() -> dict:
    if not shutil.which("nvidia-smi"):
        return {}
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                              "--format=csv,noheader"], capture_output=True, text=True, timeout=5).stdout
        name, driver, mem = [x.strip() for x in out.splitlines()[0].split(",")]
        return {"gpu_name": name, "driver": driver, "gpu_memory_total": mem}
    except Exception:
        return {}


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--limit", type=int, help="only the first N items (quick smoke test)")
    ap.add_argument("--repeats", type=int, help="override repeats from the config")
    ap.add_argument("--temperature", type=float, help="override sampling.temperature")
    ap.add_argument("--enforcement", choices=MODES, help="override enforcement mode")
    ap.add_argument("--max-retries", type=int, help="override max_retries (0 = no retry)")
    ap.add_argument("--model-label", help="override model_label (Phase 3: one config, many models)")
    ap.add_argument("--quant", help="override quant label")
    ap.add_argument("--name", help="override the experiment name")
    ap.add_argument("--repeat-index", type=int,
                    help="run exactly ONE repeat with this index (seed = base + index); used to interleave models")
    ap.add_argument("--sysmon", action="store_true", help="sample VRAM / RAM / GPU in the background (Phase 3)")
    ap.add_argument("--no-filters", action="store_true",
                    help="disable top_k / top_p / min_p (pure temperature sampling) - Phase 2 side test")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    for key, val in (("model_label", args.model_label), ("quant", args.quant), ("name", args.name)):
        if val:
            cfg[key] = val
    sampling = dict(cfg["sampling"])
    filters = "on"
    if args.no_filters:
        # top_k=0 and top_p=1.0 and min_p=0.0 switch each filter off in llama.cpp.
        sampling.update({"top_k": 0, "top_p": 1.0, "min_p": 0.0})
        filters = "off"
    if args.temperature is not None:
        sampling["temperature"] = args.temperature
    enforcement = args.enforcement or cfg.get("enforcement", "prompt_only")
    max_retries = args.max_retries if args.max_retries is not None else cfg.get("max_retries", 0)
    repeats = args.repeats or cfg.get("repeats", 5)
    warmup = cfg.get("warmup", 3)
    extra = cfg.get("extra_params", {}) or {}
    corpus_dir = (ROOT / cfg.get("corpus_dir", "second_brain_corpus/build")).resolve()

    server = LlamaServer(cfg.get("server", "http://127.0.0.1:8080"))
    server.wait_ready()
    props = server.props()

    items = load_items(corpus_dir, cfg.get("tracks", ["A", "B"]), args.limit)

    # Run name encodes the knobs being swept, so result files are self-describing.
    name = cfg["name"]
    if cfg.get("name_with_settings", False):
        name = f"{name}_{enforcement}_t{sampling['temperature']:.1f}_r{max_retries}"
        if filters == "off":
            name += "_nofilt"
    run_id = f"{name}_{datetime.now():%Y%m%d-%H%M%S}"
    out_dir = ROOT / "results" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.jsonl"

    meta = {
        "run_id": run_id, "config": cfg, "repeats": repeats, "warmup": warmup,
        "effective": {"temperature": sampling["temperature"], "enforcement": enforcement,
                      "max_retries": max_retries},
        "prompt_version": PROMPT_VERSION, "started": datetime.now().isoformat(timespec="seconds"),
        "host": {"platform": platform.platform(), "processor": platform.processor(),
                 "python": platform.python_version(), **gpu_info()},
        "server_props": {k: props.get(k) for k in ("model_path", "build_info", "total_slots", "n_ctx")
                         if k in props} | {"n_ctx": props.get("default_generation_settings", {}).get("n_ctx")},
    }
    (out_dir / f"{run_id}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    common = {"run_id": run_id, "experiment": cfg["name"], "model": cfg.get("model_label"),
              "quant": cfg.get("quant"), "prompt_version": PROMPT_VERSION,
              "temperature": sampling.get("temperature"), "seed": sampling.get("seed"),
              "enforcement": enforcement, "max_retries": max_retries, "sampling_filters": filters,
              "top_k": sampling.get("top_k"), "top_p": sampling.get("top_p"), "min_p": sampling.get("min_p")}

    # Seed per repeat. With ONE fixed seed, every repeat replays the same "random" draws, so a
    # temperature > 0 run silently becomes a single sample repeated 3x (Phase 2 smoke-run finding).
    # seed = base + repeat keeps each repeat reproducible but different. Irrelevant at temperature 0.
    vary_seed = cfg.get("vary_seed_per_repeat", True)
    base_seed = sampling.get("seed", 42)

    def seed_for(rep: int) -> int:
        return base_seed + rep if vary_seed else base_seed

    def make_generate(it: dict, rep: int):
        """The generate_fn for one item: same sampling + enforcement + seed on the first try and the retry."""
        params = {**sampling, "seed": seed_for(rep), **extra,
                  **enforcement_params(enforcement, it["track"], it["n_chunks"])}

        def generate(messages: list[dict]) -> tuple[str, dict]:
            res = server.stream_completion(server.apply_template(messages), params)
            t = res["final"].get("timings", {})
            return res["text"], {
                "ttft_ms": res["ttft_ms"], "latency_ms": res["latency_ms"],
                "prompt_n": t.get("prompt_n"), "prompt_ms": t.get("prompt_ms"),
                "prefill_tps": t.get("prompt_per_second"),
                "predicted_n": t.get("predicted_n"), "predicted_ms": t.get("predicted_ms"),
                "decode_tps": t.get("predicted_per_second"),
                "stop_type": res["final"].get("stop_type"), "truncated": res["final"].get("truncated"),
            }
        return generate

    # Warm-up: first few items, results recorded but flagged and excluded from analysis.
    schedule = [(0, True, items[i % len(items)]) for i in range(warmup)]
    rng = random.Random(cfg.get("order_seed", 1234))
    rep_indices = [args.repeat_index] if args.repeat_index else list(range(1, repeats + 1))
    for rep in rep_indices:
        order = items[:]
        if args.repeat_index:      # single-repeat mode: order depends only on the repeat index
            random.Random(cfg.get("order_seed", 1234) + rep).shuffle(order)
        else:
            rng.shuffle(order)
        schedule += [(rep, False, it) for it in order]

    total = len(schedule)
    print(f"{run_id}: {len(items)} items x {len(rep_indices)} repeat(s) + {warmup} warm-up = {total} items")
    print(f"  enforcement={enforcement}  temperature={sampling['temperature']}  max_retries={max_retries}")
    mon = SysMon(out_dir / f"{run_id}.sysmon.csv") if args.sysmon else None
    if mon:
        mon.start()
    consecutive_errors = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for seq, (rep, is_warmup, it) in enumerate(schedule, 1):
            r = generate_structured(make_generate(it, rep), it["messages"], SCHEMAS[it["track"]],
                                    n_chunks=it["n_chunks"], max_retries=max_retries)
            a1, last = r.attempts[0], r.attempts[-1]
            m1 = a1.meta
            retry_ms = sum((a.meta.get("latency_ms") or 0) for a in r.attempts[1:])
            row = {
                **common, "seq": seq, "uid": uuid.uuid4().hex[:8], "track": it["track"],
                "item_id": it["item_id"], "repeat": rep, "is_warmup": is_warmup, "seed": seed_for(rep),
                # attempt-1 timings (Phase 1 compatible)
                **{k: m1.get(k) for k in ("ttft_ms", "latency_ms", "prompt_n", "prompt_ms", "prefill_tps",
                                          "predicted_n", "predicted_ms", "decode_tps", "stop_type",
                                          "truncated")},
                "output_text": a1.raw_text,
                "error": m1.get("backend_error"),
                # structured-generation outcome
                "status": r.status,                       # ok_first / ok_retry / failed
                "n_attempts": r.n_attempts,
                "first_error_type": a1.error_type, "first_error": a1.error,
                "final_error_type": None if r.ok else last.error_type,
                "retry_output_text": r.attempts[1].raw_text if r.n_attempts > 1 else None,
                "retry_latency_ms": retry_ms if r.n_attempts > 1 else None,
                "total_latency_ms": (m1.get("latency_ms") or 0) + retry_ms,
                "final_output": r.data.model_dump(mode="json") if r.ok else None,
                "ts": datetime.now().isoformat(timespec="seconds"), **gpu_sample(),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            tag = "warm" if is_warmup else f"r{rep}"
            dec = f"{row['decode_tps']:.1f}" if row["decode_tps"] else "-"
            ttft = f"{row['ttft_ms']:.0f}" if row["ttft_ms"] else "-"
            note = {"ok_first": "", "ok_retry": f"RETRY-OK ({a1.error_type})",
                    "failed": f"FAILED ({last.error_type})"}[r.status]
            print(f"[{seq:>4}/{total}] {tag:<4} {it['item_id']}  ttft={ttft}ms  decode={dec} tok/s"
                  f"  out={row['predicted_n']}  {note}{'  ERROR ' + row['error'] if row['error'] else ''}")
            consecutive_errors = consecutive_errors + 1 if row["error"] else 0
            if consecutive_errors >= 3:
                # The server is gone (crashed, killed, or never started). Stop instead of writing
                # a whole run of failed rows that would silently pollute the results.
                if mon:
                    mon.stop()
                sys.exit(f"\nABORTED: 3 consecutive backend errors - is llama-server still running?\n"
                         f"Partial results kept in {out_path} (exclude them from analysis).")

    if mon:
        mon.stop()
        meta["sysmon"] = mon.summary()
        (out_dir / f"{run_id}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"memory: {meta['sysmon']}")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
