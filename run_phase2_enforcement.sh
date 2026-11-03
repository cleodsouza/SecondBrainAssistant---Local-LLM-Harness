#!/usr/bin/env bash
# Phase 2.3 - enforcement comparison: 3 modes x 2 temperatures, 3 repeats each (~35 min total).
# Usage (from "D:\SLM Project", venv active, llama-server running):
#   bash run_phase2_enforcement.sh
#   bash run_phase2_enforcement.sh --limit 4 --repeats 1     # ~2 min smoke test of all 6 settings
set -euo pipefail
cd "$(dirname "$0")"

# Refuse to run outside the project venv (the system Python 3.9 has incompatible pandas/numpy).
python -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" || {
  echo "Activate the project venv first:  source second_brain_corpus/.venv/Scripts/activate"; exit 1; }

CONFIG=configs/phase2_base.yaml
EXTRA=("$@")                       # pass-through, e.g. --limit 4 --repeats 1
mkdir -p results
RUNS=()

for TEMP in 0.0 0.7; do
  for MODE in prompt_only json_object json_schema; do
    echo "=============== enforcement=$MODE  temperature=$TEMP ==============="
    LOG="results/phase2_${MODE}_t${TEMP}_console.log"
    python harness/runner.py --config "$CONFIG" --enforcement "$MODE" --temperature "$TEMP" "${EXTRA[@]}" | tee "$LOG"
    RUN_FILE=$(grep -o 'wrote .*\.jsonl' "$LOG" | tail -1 | sed 's/^wrote //')
    [ -n "$RUN_FILE" ] || { echo "Could not find the results file for $MODE / $TEMP"; exit 1; }
    RUNS+=("$RUN_FILE")
  done
done

echo "=============== Analysis ==============="
python harness/analyze_phase2.py --label enforcement "${RUNS[@]}"
