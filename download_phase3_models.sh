#!/usr/bin/env bash
# Download the Phase 3 models (Q4_K_M GGUF, from unsloth on Hugging Face) straight to D:\models.
# ~9.6 GB total. Safe to re-run: curl resumes partial downloads (-C -).
# Usage (Git Bash):  bash download_phase3_models.sh
set -euo pipefail
DEST=/d/models
mkdir -p "$DEST"

download() {   # download <hf repo> <file>
  local URL="https://huggingface.co/$1/resolve/main/$2"
  echo "=== $2"
  curl -L --fail --retry 5 -C - -o "$DEST/$2" "$URL"
}

download unsloth/gemma-4-E4B-it-GGUF  gemma-4-E4B-it-Q4_K_M.gguf     # 4.98 GB
download unsloth/granite-4.1-3b-GGUF  granite-4.1-3b-Q4_K_M.gguf     # 2.10 GB
download unsloth/Phi-4-mini-instruct-GGUF  Phi-4-mini-instruct-Q4_K_M.gguf   # 2.49 GB

echo
ls -lh "$DEST"/*.gguf
