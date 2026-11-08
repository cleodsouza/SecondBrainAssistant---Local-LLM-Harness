#!/usr/bin/env bash
# Phase 4 - fidelity check that does not depend on our grader: KL divergence of every quantized version's
# next-token probabilities against the BF16 original, plus perplexity, on the same text.
#   KLD 0 = identical behaviour; "same top token" = how often the quantized model's most likely next token
#   matches the original's. Standard llama.cpp quantization metric.
# Text: all 60 corpus notes concatenated (domain text; it measures distribution drift, not answers).
# ~10 min. Usage (venv active, no server running):  bash run_phase4_kld.sh
set -euo pipefail
cd "$(dirname "$0")"
python -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" || {
  echo "Activate the project venv first:  source second_brain_corpus/.venv/Scripts/activate"; exit 1; }

PPL=./llama-bin/llama-perplexity.exe
DEST=/d/models/phase4
BASE=$DEST/kld_base_bf16.bin
TEXT=results/phase4_eval_text.txt
LOGS=results/kld_logs
mkdir -p "$LOGS" results/raw

taskkill //IM llama-server.exe //F >/dev/null 2>&1 || true   # free the GPU

python - <<'EOF'
import json
notes = [json.loads(l) for l in open("second_brain_corpus/build/notes.jsonl", encoding="utf-8")]
text = "\n\n".join(f"Note {n['id']} ({n['created']}):\n{n['body'].strip()}" for n in notes)
open("results/phase4_eval_text.txt", "w", encoding="utf-8", newline="\n").write(text)
print(f"eval text: {len(text.split())} words")
EOF

echo "=== BF16 reference (saves its token probabilities to $BASE)"
"$PPL" -m "$DEST/granite-4.1-3b-BF16.gguf" -f "$TEXT" -c 512 -ngl 99 --kl-divergence-base "$BASE" \
  > "$LOGS/granite-BF16.log" 2>&1 || { tail -15 "$LOGS/granite-BF16.log"; exit 1; }

mapfile -t ROWS < <(python -c "
import yaml
for m in yaml.safe_load(open('configs/phase4_models.yaml'))['models']:
    if m['quant'] != 'BF16': print(m['label'] + '|' + m['path'])
" | tr -d '\r')

for ROW in "${ROWS[@]}"; do
  IFS='|' read -r LABEL MPATH <<< "$ROW"
  echo "=== $LABEL"
  "$PPL" -m "$MPATH" -f "$TEXT" -c 512 -ngl 99 --kl-divergence-base "$BASE" --kl-divergence \
    > "$LOGS/$LABEL.log" 2>&1 || { echo "failed:"; tail -15 "$LOGS/$LABEL.log"; exit 1; }
done

python harness/parse_kld.py "$LOGS" results/raw/phase4_kld.csv
