#!/usr/bin/env bash
# Start llama-server with the pinned pilot model (works offline). Leave this window open.
# Usage (from "D:\SLM Project"):   bash start_server.sh
#        other model:              bash start_server.sh "C:/path/to/model.gguf"
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${1:-C:/Users/cleon/.cache/huggingface/hub/models--unsloth--Qwen3-4B-Instruct-2507-GGUF/snapshots/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf}"

# Ollama keeps models loaded on the GPU and skews benchmarks - stop it if it's running.
taskkill //IM "ollama app.exe" //F >/dev/null 2>&1 || true
taskkill //IM ollama.exe //F >/dev/null 2>&1 || true

echo "Starting llama-server with: $MODEL"
./llama-bin/llama-server.exe -m "$MODEL" -ngl 99 -c 8192 --port 8080 --seed 42
