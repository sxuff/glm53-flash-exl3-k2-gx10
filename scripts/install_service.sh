#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_ROOT="${1:-$HOME/models/GLM-5.3-Flash-EXL3-K2}"
RECIPE_ROOT="${2:-$HOME/src/GLM-5.3-Flash-EXL3-K2-DGX-Spark-recipe-0b8dd0d6}"
VENV="${3:-$HOME/venvs/glm53-exl3-local}"
ENV_DIR="$HOME/.config/glm53-exl3-k2"
UNIT_DIR="$HOME/.config/systemd/user"

[[ -f "$MODEL_ROOT/config.json" ]] || { printf 'missing model: %s\n' "$MODEL_ROOT" >&2; exit 1; }
[[ -f "$RECIPE_ROOT/scripts/serve_one_spark.sh" ]] || { printf 'missing pinned upstream recipe: %s\n' "$RECIPE_ROOT" >&2; exit 1; }
[[ -x "$VENV/bin/python" ]] || { printf 'missing runtime venv: %s\n' "$VENV" >&2; exit 1; }

mkdir -p "$HOME/.local/bin" "$ENV_DIR" "$UNIT_DIR"
install -m 0755 "$ROOT/scripts/run_server.sh" "$HOME/.local/bin/run-glm53-exl3-k2.sh"
install -m 0644 "$ROOT/systemd/glm53-exl3-k2.service" "$UNIT_DIR/glm53-exl3-k2.service"
printf '%s\n' \
  "MODEL_ROOT=$MODEL_ROOT" \
  "RECIPE_ROOT=$RECIPE_ROOT" \
  "VENV=$VENV" \
  "HOST=127.0.0.1" \
  "PORT=8888" \
  "SERVED_NAME=glm53-flash-exl3-k2" \
  "SPEC_METHOD=mtp" \
  "MTP_TOKENS=2" \
  "MAX_MODEL_LEN=65536" \
  "MAX_NUM_SEQS=1" \
  "MAX_NUM_BATCHED_TOKENS=2048" \
  "GPU_MEM_UTIL=0.87" \
  "EXL3_FUSED_MOE=1" > "$ENV_DIR/server.env"
chmod 0600 "$ENV_DIR/server.env"
systemctl --user daemon-reload
printf 'installed. Start with:\n  systemctl --user enable --now glm53-exl3-k2.service\n'
