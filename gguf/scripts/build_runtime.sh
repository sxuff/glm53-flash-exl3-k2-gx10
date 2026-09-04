#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-$REPO_ROOT/runtime/llama.cpp}"
BUILD_DIR="${BUILD_DIR:-$SOURCE_DIR/build-gb10}"
RUNTIME_REPO="https://github.com/unslothai/llama.cpp.git"
RUNTIME_REV="629b50552801912b3e2078f9799e4d77213197d7"
PATCH="$REPO_ROOT/patches/gguf-canonical-naming.patch"

if [[ ! -d "$SOURCE_DIR/.git" ]]; then
  mkdir -p "$(dirname "$SOURCE_DIR")"
  git clone --filter=blob:none --no-checkout "$RUNTIME_REPO" "$SOURCE_DIR"
fi

git -C "$SOURCE_DIR" fetch --no-tags origin "$RUNTIME_REV"
test "$(git -C "$SOURCE_DIR" rev-parse FETCH_HEAD)" = "$RUNTIME_REV"
git -C "$SOURCE_DIR" checkout --detach "$RUNTIME_REV"
git -C "$SOURCE_DIR" reset --hard "$RUNTIME_REV"
git -C "$SOURCE_DIR" clean -ffd
git -C "$SOURCE_DIR" apply --check "$PATCH"
git -C "$SOURCE_DIR" apply "$PATCH"
git -C "$SOURCE_DIR" diff --check

export PATH="${CUDA_HOME:-/usr/local/cuda-13.0}/bin:$PATH"
export CUDACXX="${CUDACXX:-${CUDA_HOME:-/usr/local/cuda-13.0}/bin/nvcc}"

cmake -S "$SOURCE_DIR" -B "$BUILD_DIR" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=ON \
  -DGGML_CUDA=ON \
  -DGGML_CURL=ON \
  -DLLAMA_BUILD_UI=OFF \
  -DCMAKE_CUDA_COMPILER="$CUDACXX" \
  -DCMAKE_CUDA_ARCHITECTURES=121
cmake --build "$BUILD_DIR" --config Release --target llama-server llama-bench -j"${JOBS:-$(nproc)}"
"$BUILD_DIR/bin/llama-server" --version
"$BUILD_DIR/bin/llama-server" --list-devices
