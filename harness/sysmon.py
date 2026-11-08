"""
Phase 3 - background memory / GPU sampler.

Phase 1 sampled the GPU only *after* each request, when it was already idling, so clock readings were
meaningless and peaks were missed. This runs in a background thread for the whole run instead:

  - nvidia-smi in loop mode (-lms) streams one line every INTERVAL_MS: VRAM used, GPU util, SM clock,
    temperature, power  -> no per-sample process start-up cost
  - psutil polls the llama-server process: resident RAM (RSS)

    with SysMon(out_csv) as mon:
        ... run the benchmark ...
    mon.summary()  -> {"vram_start_mib", "vram_peak_mib", "ram_peak_mib", "gpu_util_mean", ...}

`vram_start_mib` is sampled before the first request (model loaded, idle) - that is the model's
resident footprint; `vram_peak_mib` adds the KV cache and compute buffers in use during generation.
"""
from __future__ import annotations

import csv
import shutil
import subprocess
import threading
import time
from pathlib import Path

INTERVAL_MS = 250
FIELDS = ["t", "vram_used_mib", "gpu_util_pct", "sm_clock_mhz", "gpu_temp_c", "gpu_power_w", "server_rss_mib"]


def _find_server_process(name: str = "llama-server"):
    try:
        import psutil
    except ImportError:
        return None
    for p in psutil.process_iter(["name"]):
        if p.info["name"] and p.info["name"].lower().startswith(name):
            return p
    return None


class SysMon:
    def __init__(self, out_csv: Path, interval_ms: int = INTERVAL_MS):
        self.out_csv = Path(out_csv)
        self.interval_ms = interval_ms
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self._proc = None
        self._threads: list[threading.Thread] = []
        self._rss_mib = None

    # ---- context manager
    def __enter__(self) -> "SysMon":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    # ---- lifecycle
    def start(self) -> None:
        self._t0 = time.perf_counter()
        server = _find_server_process()
        if server is not None:
            t = threading.Thread(target=self._poll_rss, args=(server,), daemon=True)
            t.start(); self._threads.append(t)
        if shutil.which("nvidia-smi"):
            self._proc = subprocess.Popen(
                ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu,clocks.sm,temperature.gpu,power.draw",
                 "--format=csv,noheader,nounits", "-lms", str(self.interval_ms)],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
            t = threading.Thread(target=self._read_gpu, daemon=True)
            t.start(); self._threads.append(t)
        time.sleep(self.interval_ms / 1000 * 2)       # make sure the idle "start" sample exists

    def stop(self) -> None:
        self._stop.set()
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
        for t in self._threads:
            t.join(timeout=2)
        self._write()

    # ---- workers
    def _poll_rss(self, server) -> None:
        while not self._stop.is_set():
            try:
                self._rss_mib = server.memory_info().rss / 2**20
            except Exception:
                return
            time.sleep(self.interval_ms / 1000)

    def _read_gpu(self) -> None:
        for line in self._proc.stdout:
            if self._stop.is_set():
                break
            parts = [x.strip() for x in line.split(",")]
            if len(parts) != 5:
                continue
            try:
                vals = [float(x) for x in parts]
            except ValueError:
                continue
            self.samples.append(dict(zip(FIELDS, [round(time.perf_counter() - self._t0, 3), *vals,
                                                  round(self._rss_mib, 1) if self._rss_mib else None])))

    def _write(self) -> None:
        self.out_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(self.out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(self.samples)

    # ---- results
    def summary(self) -> dict:
        s = self.samples
        if not s:
            return {"sysmon": "no samples (nvidia-smi missing?)"}
        vram = [x["vram_used_mib"] for x in s]
        rss = [x["server_rss_mib"] for x in s if x["server_rss_mib"]]
        util = [x["gpu_util_pct"] for x in s]
        busy = [x for x in s if x["gpu_util_pct"] >= 30]
        return {
            "vram_start_mib": vram[0],
            "vram_peak_mib": max(vram),
            "ram_peak_mib": max(rss) if rss else None,
            "gpu_util_mean": round(sum(util) / len(util), 1),
            "sm_clock_busy_median_mhz": sorted(x["sm_clock_mhz"] for x in busy)[len(busy) // 2] if busy else None,
            "gpu_temp_max_c": max(x["gpu_temp_c"] for x in s),
            "gpu_power_busy_median_w": sorted(x["gpu_power_w"] for x in busy)[len(busy) // 2] if busy else None,
            "n_samples": len(s),
        }
