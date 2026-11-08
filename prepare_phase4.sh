#!/usr/bin/env bash
# Phase 4 - build the quantized versions of Granite 4.1 3B from its full-precision (BF16) weights.
#   1. download the official BF16 GGUF (6.8 GB) + unsloth's importance matrix (3.8 MB) to D:\models\phase4
#   2. llama-quantize -> Q8_0 Q6_K Q5_K_M Q4_K_M Q3_K_M Q2_K           (plain)
#                     -> Q4_K_M Q3_K_M Q2_K with --imatrix             (calibrated; matters most at low bits)
# ~10 min download + ~5-10 min quantizing, ~26 GB on D:. Safe to re-run: finished files are skipped.
# Usage (Git Bash, from "D:\SLM Project"):  bash prepare_phase4.sh
set -euo pipefail
cd "$(dirname "$0")"

DEST=/d/models/phase4
QUANTIZE=./llama-bin/llama-quantize.exe
REPO=unsloth/granite-4.1-3b-GGUF
mkdir -p "$DEST" results/quantize_logs

download() {   # download <file in repo> <local name>
  local URL="https://huggingface.co/$REPO/resolve/main/$1" OUT="$DEST/$2" REMOTE LOCAL
  echo "=== download $1"
  REMOTE=$(curl -sIL "$URL" | grep -i '^content-length' | tail -1 | tr -dc '0-9')
  LOCAL=$(stat -c %s "$OUT" 2>/dev/null || echo 0)
  if [ -n "$REMOTE" ] && [ "$LOCAL" = "$REMOTE" ]; then echo "already complete - skipping"; return 0; fi
  curl -L --fail --retry 5 -C - -o "$OUT" "$URL"
}

download granite-4.1-3b-BF16.gguf        granite-4.1-3b-BF16.gguf
download imatrix_unsloth.gguf_file       imatrix_unsloth.gguf

SRC="$DEST/granite-4.1-3b-BF16.gguf"
IMAT="$DEST/imatrix_unsloth.gguf"

quantize() {   # quantize <TYPE> [imat]
  local TYPE=$1 TAG="" ARGS=()
  if [ "${2:-}" = "imat" ]; then TAG="-imat"; ARGS=(--imatrix "$IMAT"); fi
  local OUT="$DEST/granite-4.1-3b-${TYPE}${TAG}.gguf"
  if [ -f "$OUT" ]; then echo "=== $TYPE$TAG exists - skipping"; return 0; fi
  echo "=== quantize $TYPE$TAG"
  local START=$SECONDS
  # write to a temp name first, so an interrupted run never leaves a half-written file that looks finished
  "$QUANTIZE" "${ARGS[@]}" "$SRC" "$OUT.part" "$TYPE" 8 > "results/quantize_logs/${TYPE}${TAG}.log" 2>&1 \
    || { echo "llama-quantize failed for $TYPE$TAG:"; tail -15 "results/quantize_logs/${TYPE}${TAG}.log"; exit 1; }
  mv "$OUT.part" "$OUT"
  echo "    done in $((SECONDS - START)) s, $(du -h "$OUT" | cut -f1)"
}

for T in Q8_0 Q6_K Q5_K_M Q4_K_M Q3_K_M Q2_K; do quantize "$T"; done
for T in Q4_K_M Q3_K_M Q2_K; do quantize "$T" imat; done

echo
ls -lh "$DEST"/*.gguf
