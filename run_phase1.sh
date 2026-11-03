#!/usr/bin/env bash
# Phase 1 baseline: two full runs back to back, then analysis of both.
# Usage (from "D:\SLM Project", with the venv active and llama-server running):
#   bash run_phase1.sh                       # default config
#   bash run_phase1.sh configs/other.yaml    # any other config
set -euo pipefail
cd "$(dirname "$0")"

# Refuse to run outside the project venv (the system Python 3.9 has incompatible pandas/numpy).
python -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" || {
  echo "Activate the project venv first:  source second_brain_corpus/.venv/Scripts/activate"; exit 1; }

CONFIG="${1:-configs/phase1_pilot.yaml}"
RUNS=()

for i in 1 2; do
  echo "=================== Phase 1 run $i of 2 ($CONFIG) ==================="
  LOG="results/run${i}_console.log"
  mkdir -p results
  python harness/runner.py --config "$CONFIG" | tee "$LOG"
  # the runner's last lines contain:  wrote <path>.jsonl
  RUN_FILE=$(grep -o 'wrote .*\.jsonl' "$LOG" | tail -1 | sed 's/^wrote //')
  [ -n "$RUN_FILE" ] || { echo "Could not find the results file for run $i"; exit 1; }
  RUNS+=("$RUN_FILE")
  echo "run $i -> $RUN_FILE"
done

echo "=================== Analysis ==================="
python harness/analyze_phase1.py "${RUNS[@]}"
