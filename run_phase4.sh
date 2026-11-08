#!/usr/bin/env bash
# Phase 4 - benchmark all 11 Granite versions with the exact Phase 3 runner (server restart per version,
# order rotated each round, background memory sampling, model-file check), schema mode, 2 rounds.
# Quality is deterministic at temperature 0, so 2 rounds are enough; the second round measures speed noise.
# Context 4096 (not 8192) for ALL versions: BF16 (6.5 GiB) + an 8k KV cache nearly fills the 8 GB GPU and Windows
# silently spills to system RAM (smoke test: SM clock 210 MHz, 17 tok/s). Longest prompt+answer is ~1.6k tokens.
# ~60-75 min. Usage (venv active, no server running):
#   bash run_phase4.sh              # full run
#   bash run_phase4.sh --limit 4    # smoke test
set -euo pipefail
cd "$(dirname "$0")"
MODELS_CFG=configs/phase4_models.yaml \
CONFIG=configs/phase3_base.yaml \
ROUNDS=${ROUNDS:-2} \
MODES=${MODES:-json_schema} \
PREFIX=phase4 \
CTX=${CTX:-4096} \
ANALYZE=harness/analyze_phase4.py \
  bash run_phase3.sh "$@"
