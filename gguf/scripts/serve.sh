#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${MODE:-mtp}"
LLAMA_ROOT="${LLAMA_ROOT:-$REPO_ROOT/runtime/llama.cpp}"
BUILD_DIR="${BUILD_DIR:-$LLAMA_ROOT/build-gb10}"
MODEL_DIR="${MODEL_DIR:?set MODEL_DIR to the verified UD-IQ2_XXS directory}"
MODEL="${MODEL:-$MODEL_DIR/GLM-5.3-Flash-UD-IQ2_XXS-00001-of-00004.gguf}"
MMPROJ="${MMPROJ:-}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8001}"
CTX="${CTX:-8192}"

args=(
  --model "$MODEL"
  --host "$HOST"
  --port "$PORT"
  --ctx-size "$CTX"
  --parallel 1
  --n-gpu-layers all
  --flash-attn on
  --metrics
  --no-webui
)

if [[ -n "$MMPROJ" ]]; then
  args+=(--mmproj "$MMPROJ")
fi

case "$MODE" in
  mtp)
    args+=(--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 0)
    ;;
  no-mtp)
    args+=(--spec-type none)
    ;;
  *)
    printf 'MODE must be mtp or no-mtp\n' >&2
    exit 2
    ;;
esac

exec "$BUILD_DIR/bin/llama-server" "${args[@]}"
