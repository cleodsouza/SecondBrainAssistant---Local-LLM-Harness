#!/usr/bin/env bash
# Phase 3 - model comparison. For each of 3 rounds, for each model (order rotated every round):
#   restart llama-server with that model (-np 1), then run json_schema AND prompt_only (1 repeat each)
#   with background VRAM/RAM sampling. Interleaving means slow drift (heat, background load) is spread
#   across all models instead of hitting whichever runs last.
# ~100-120 min for 4 models. Usage (from "D:\SLM Project", venv active, Ollama closed, NO server running):
#   bash run_phase3.sh                          # full comparison
#   bash run_phase3.sh --limit 4                # smoke test: 4 items, still all models / rounds
set -euo pipefail
cd "$(dirname "$0")"

python -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" || {
  echo "Activate the project venv first:  source second_brain_corpus/.venv/Scripts/activate"; exit 1; }

# Overridable from the environment, so Phase 4 reuses this exact script (see run_phase4.sh).
MODELS_CFG=${MODELS_CFG:-configs/phase3_models.yaml}
CONFIG=${CONFIG:-configs/phase3_base.yaml}
ROUNDS=${ROUNDS:-3}
MODES=${MODES:-"json_schema prompt_only"}
PREFIX=${PREFIX:-phase3}
ANALYZE=${ANALYZE:-harness/analyze_phase3.py}
CTX=${CTX:-8192}
EXTRA=("$@")
SERVER=./llama-bin/llama-server.exe
mkdir -p results/raw results/server_logs
IDLE_CSV=results/raw/${PREFIX}_idle_vram.csv
[ -f "$IDLE_CSV" ] || echo "timestamp,label,vram_idle_mib" > "$IDLE_CSV"

# label|quant|path per model; refuse to start if any TODO is left
mapfile -t MODELS < <(python -c "
import yaml,sys
ms=yaml.safe_load(open('$MODELS_CFG'))['models']
bad=[m['label'] for m in ms if 'TODO' in (str(m['path'])+str(m['quant']))]
if bad: sys.exit('Fill path/quant in $MODELS_CFG for: '+', '.join(bad))
import os
missing=[m['label'] for m in ms if not os.path.exists(m['path'])]
if missing: sys.exit('Model file not found for: '+', '.join(missing))
print('\n'.join(f\"{m['label']}|{m['quant']}|{m['path']}|{m.get('server_args','')}\" for m in ms))
" | tr -d '\r')   # Windows Python ends lines with \r\n; a stray \r became a bogus server argument
N=${#MODELS[@]}
[ "$N" -gt 0 ] || { echo "No models read from $MODELS_CFG (see the error above)."; exit 1; }
RUNS=()

stop_server() {
  taskkill //IM llama-server.exe //F >/dev/null 2>&1 || true
  taskkill //IM "ollama app.exe" //F >/dev/null 2>&1 || true
  taskkill //IM ollama.exe //F >/dev/null 2>&1 || true
  # Wait until port 8080 is really free - otherwise the NEXT server fails to bind while the old one
  # still answers the health check, and we'd benchmark the wrong model (found in the mock test).
  for _ in $(seq 1 30); do
    curl -s -m 2 http://127.0.0.1:8080/health >/dev/null 2>&1 || return 0
    sleep 1
  done
  echo "Port 8080 is still in use after 30 s - close whatever is using it and re-run."; exit 1
}

start_server() {   # start_server <label> <path> [extra server args]
  stop_server
  local VRAM
  VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' \r')
  echo "$(date +%Y-%m-%dT%H:%M:%S),$1,$VRAM" >> "$IDLE_CSV"
  echo "---- starting llama-server: $1 (idle VRAM before load: ${VRAM} MiB)"
  # shellcheck disable=SC2086  (extra args are intentionally word-split)
  "$SERVER" -m "$2" -ngl 99 -c "$CTX" -np 1 --port 8080 --seed 42 ${3:-} > "results/server_logs/$1.log" 2>&1 &
  local PID=$!
  for _ in $(seq 1 90); do
    if ! kill -0 "$PID" 2>/dev/null; then
      echo "llama-server exited while loading $1 - last log lines:"; tail -20 "results/server_logs/$1.log"; exit 1
    fi
    if curl -s -m 2 http://127.0.0.1:8080/health | grep -q '"ok"'; then
      # Make sure the server that answered is serving THIS model file.
      curl -s -m 5 http://127.0.0.1:8080/props | python -c "
import json,sys,os
got=os.path.basename(str(json.load(sys.stdin).get('model_path','')).replace(chr(92),'/'))
want=os.path.basename(sys.argv[1].replace(chr(92),'/'))
sys.exit(0 if got==want else f'Server is serving {got!r}, expected {want!r}')" "$2" || exit 1
      return 0
    fi
    sleep 2
  done
  echo "llama-server did not become ready for $1 - last log lines:"; tail -20 "results/server_logs/$1.log"; exit 1
}

trap stop_server EXIT

for ROUND in $(seq 1 $ROUNDS); do
  for ((k = 0; k < N; k++)); do
    IFS='|' read -r LABEL QUANT MPATH SARGS <<< "${MODELS[$(( (k + ROUND - 1) % N ))]}"
    start_server "$LABEL" "$MPATH" "$SARGS"
    for MODE in $MODES; do
      echo "=============== round $ROUND/$ROUNDS  $LABEL  $MODE ==============="
      LOG="results/server_logs/console_${LABEL}_${MODE}_r${ROUND}.log"
      python harness/runner.py --config "$CONFIG" --model-label "$LABEL" --quant "$QUANT" \
        --name "${PREFIX}_${LABEL}" --enforcement "$MODE" --repeat-index "$ROUND" --sysmon "${EXTRA[@]}" | tee "$LOG"
      FILE=$(grep -o 'wrote .*\.jsonl' "$LOG" | tail -1 | sed 's/^wrote //' | tr -d '\r')
      [ -n "$FILE" ] || { echo "No results file for $LABEL $MODE round $ROUND"; exit 1; }
      RUNS+=("$FILE")
    done
  done
done

stop_server
echo "=============== Analysis ==============="
python "$ANALYZE" "${RUNS[@]}"
