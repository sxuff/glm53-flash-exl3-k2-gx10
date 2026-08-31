#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/vcruz305/GLM-5.3-Flash-EXL3-K2-DGX-Spark-recipe.git}"
UPSTREAM_COMMIT="${UPSTREAM_COMMIT:-0b8dd0d6c7b186076f2e61d1b99a6289f8006c3c}"
RECIPE_ROOT="${RECIPE_ROOT:-$HOME/src/GLM-5.3-Flash-EXL3-K2-DGX-Spark-recipe-0b8dd0d6}"
VENV="${VENV:-$HOME/venvs/glm53-exl3-local}"

[[ "$(uname -m)" == "aarch64" ]] || { printf 'aarch64 is required\n' >&2; exit 1; }
command -v git >/dev/null || { printf 'git is required\n' >&2; exit 1; }
command -v python3.12 >/dev/null || { printf 'python3.12 is required\n' >&2; exit 1; }
command -v nvcc >/dev/null || {
  if [[ -x /usr/local/cuda-13.0/bin/nvcc ]]; then
    export PATH="/usr/local/cuda-13.0/bin:$PATH"
  else
    printf 'CUDA 13 nvcc is required\n' >&2
    exit 1
  fi
}

python3.12 -m venv "$VENV"
if ! python3.12 - <<'PY'
import pathlib, sysconfig
path = pathlib.Path(sysconfig.get_paths()["include"]) / "Python.h"
raise SystemExit(0 if path.is_file() else 1)
PY
then
  printf 'warning: Python.h is missing. Install python3.12-dev before a native wheel fallback build.\n' >&2
fi

mkdir -p "$RECIPE_ROOT"
if [[ ! -d "$RECIPE_ROOT/.git" ]]; then
  git -C "$RECIPE_ROOT" init
  git -C "$RECIPE_ROOT" remote add origin "$UPSTREAM_REPO"
fi
actual_origin="$(git -C "$RECIPE_ROOT" remote get-url origin)"
[[ "$actual_origin" == "$UPSTREAM_REPO" ]] || {
  printf 'unexpected upstream remote: %s\n' "$actual_origin" >&2
  exit 1
}
git -C "$RECIPE_ROOT" fetch --depth 1 origin "$UPSTREAM_COMMIT"
[[ "$(git -C "$RECIPE_ROOT" rev-parse FETCH_HEAD)" == "$UPSTREAM_COMMIT" ]] || {
  printf 'upstream commit verification failed\n' >&2
  exit 1
}
git -C "$RECIPE_ROOT" checkout --detach --force FETCH_HEAD
[[ "$(git -C "$RECIPE_ROOT" rev-parse HEAD)" == "$UPSTREAM_COMMIT" ]] || exit 1

VENV="$VENV" bash "$RECIPE_ROOT/scripts/install_prebuilt.sh"
printf 'runtime ready\nrecipe=%s\ncommit=%s\nvenv=%s\n' "$RECIPE_ROOT" "$UPSTREAM_COMMIT" "$VENV"
