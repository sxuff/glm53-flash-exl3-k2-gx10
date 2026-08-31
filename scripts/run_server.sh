#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="${ENV_FILE:-$HOME/.config/glm53-exl3-k2/server.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

RECIPE_ROOT="${RECIPE_ROOT:-$HOME/src/GLM-5.3-Flash-EXL3-K2-DGX-Spark-recipe-0b8dd0d6}"
VENV="${VENV:-$HOME/venvs/glm53-exl3-local}"
MODEL_ROOT="${MODEL_ROOT:-$HOME/models/GLM-5.3-Flash-EXL3-K2}"
PYDEV_ROOT="${PYDEV_ROOT:-$HOME/.local/python312-dev/root}"

[[ "$(uname -m)" == "aarch64" ]] || { printf 'aarch64 is required\n' >&2; exit 1; }
[[ -x "$VENV/bin/python" ]] || { printf 'runtime venv missing: %s\n' "$VENV" >&2; exit 1; }
[[ -f "$RECIPE_ROOT/scripts/serve_one_spark.sh" ]] || { printf 'pinned upstream recipe missing: %s\n' "$RECIPE_ROOT" >&2; exit 1; }
[[ -f "$MODEL_ROOT/config.json" ]] || { printf 'model missing: %s\n' "$MODEL_ROOT" >&2; exit 1; }

export PATH="/usr/local/cuda-13.0/bin:$VENV/bin:$PATH"
if [[ -f "$PYDEV_ROOT/usr/include/python3.12/Python.h" ]]; then
  export CPATH="$PYDEV_ROOT/usr/include/python3.12:$PYDEV_ROOT/usr/include${CPATH:+:$CPATH}"
  export LIBRARY_PATH="$PYDEV_ROOT/usr/lib/aarch64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
fi
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-$HOME/.cache/triton-glm53-exl3}"
mkdir -p "$TRITON_CACHE_DIR"
source "$VENV/bin/activate"
python "$RECIPE_ROOT/scripts/preflight.py" --model-dir "$MODEL_ROOT"
python "$RECIPE_ROOT/scripts/patch_chat_template_thinking.py" "$MODEL_ROOT/chat_template.jinja"

exec env \
  VENV="$VENV" \
  MODEL_DIR="$MODEL_ROOT" \
  HOST="${HOST:-127.0.0.1}" \
  PORT="${PORT:-8888}" \
  SERVED_NAME="${SERVED_NAME:-glm53-flash-exl3-k2}" \
  SPEC_METHOD="${SPEC_METHOD:-mtp}" \
  MTP_TOKENS="${MTP_TOKENS:-2}" \
  MAX_MODEL_LEN="${MAX_MODEL_LEN:-65536}" \
  MAX_NUM_SEQS="${MAX_NUM_SEQS:-1}" \
  MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-2048}" \
  GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.87}" \
  EXL3_FUSED_MOE="${EXL3_FUSED_MOE:-1}" \
  bash "$RECIPE_ROOT/scripts/serve_one_spark.sh"
