#!/usr/bin/env bash
# Print the GGUF file path, quantization and architecture behind Ollama model tags, ready to paste into
# configs/phase3_models.yaml. Ollama must be running (Start menu -> Ollama, or `ollama serve`).
# Usage:  bash find_ollama_gguf.sh llama3.2:latest phi4-mini qwen3.5:4b
set -uo pipefail
for TAG in "$@"; do
  echo "# ---- $TAG"
  FROM=$(ollama show --modelfile "$TAG" 2>/dev/null | grep -m1 '^FROM ' | sed 's/^FROM //')
  if [ -z "$FROM" ]; then echo "#   not found - pull it first:  ollama pull $TAG"; continue; fi
  INFO=$(ollama show "$TAG" 2>/dev/null)
  ARCH=$(echo "$INFO"  | awk '/architecture/ {print $2; exit}')
  PARAM=$(echo "$INFO" | awk '/parameters/   {print $2; exit}')
  QUANT=$(echo "$INFO" | awk '/quantization/ {print $2; exit}')
  PROJ=$(echo "$INFO"  | grep -ci 'projector')
  echo "#   architecture=$ARCH  parameters=$PARAM  quantization=$QUANT  vision_projector=$([ "$PROJ" -gt 0 ] && echo yes || echo no)"
  echo "    quant: $QUANT"
  echo "    path: \"$(echo "$FROM" | sed 's#\\#/#g')\""
done
