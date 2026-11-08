#!/usr/bin/env bash
# Phase 2.5 - temperature sweep: prompt_only and json_schema x temperatures 0 / 0.2 / 0.4 / 0.6 / 0.7,
# 3 repeats each with a different seed per repeat, plus a side test at 0.7 with sampling filters OFF.
# 12 runs, ~75 min. Usage (from "D:\SLM Project", venv active, llama-server running, Ollama closed):
#   bash run_phase2_temperature.sh
#   bash run_phase2_temperature.sh --limit 4 --repeats 2      # ~5 min smoke test
set -euo pipefail
cd "$(dirname "$0")"

python -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" || {
  echo "Activate the project venv first:  source second_brain_corpus/.venv/Scripts/activate"; exit 1; }

CONFIG=configs/phase2_base.yaml
EXTRA=("$@")
mkdir -p results
RUNS=()

run() {   # run <mode> <temp> [--no-filters]
  local MODE=$1 TEMP=$2; shift 2
  local TAG="${MODE}_t${TEMP}${1:+_nofilt}"
  echo "=============== $TAG ==============="
  local LOG="results/phase2T_${TAG}_console.log"
  python harness/runner.py --config "$CONFIG" --enforcement "$MODE" --temperature "$TEMP" "$@" "${EXTRA[@]}" | tee "$LOG"
  local FILE
  FILE=$(grep -o 'wrote .*\.jsonl' "$LOG" | tail -1 | sed 's/^wrote //')
  [ -n "$FILE" ] || { echo "Could not find the results file for $TAG"; exit 1; }
  RUNS+=("$FILE")
}

# Interleave the two modes at each temperature, so slow drift (heat, background load) hits both equally.
for TEMP in 0.0 0.2 0.4 0.6 0.7; do
  run prompt_only "$TEMP"
  run json_schema "$TEMP"
done
# Side test: same temperature, sampling filters off - how much do top_k / top_p / min_p protect the output?
run prompt_only 0.7 --no-filters
run json_schema 0.7 --no-filters

echo "=============== Analysis ==============="
python harness/analyze_temperature.py "${RUNS[@]}"
