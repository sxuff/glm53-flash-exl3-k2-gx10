#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${MANIFEST:-$ROOT/manifests/glm53-exl3-k2.json}"
DEST="${DEST:-$HOME/models/GLM-5.3-Flash-EXL3-K2}"

command -v hf >/dev/null || {
  printf 'Install the Hugging Face CLI in the runtime venv first.\n' >&2
  exit 1
}
repo="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repository"])' "$MANIFEST")"
revision="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["revision"])' "$MANIFEST")"
mkdir -p "$DEST"
printf 'downloading %s@%s to %s\n' "$repo" "$revision" "$DEST"
hf download "$repo" --revision "$revision" --local-dir "$DEST"
python3 "$ROOT/scripts/verify_model.py" --manifest "$MANIFEST" --model-root "$DEST"
