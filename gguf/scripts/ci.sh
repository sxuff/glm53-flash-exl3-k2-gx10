#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

bash -n scripts/build_runtime.sh scripts/serve.sh scripts/ci.sh
python3 -m py_compile scripts/download.py scripts/benchmark.py scripts/analyze.py scripts/verify.py tests/test_contracts.py
python3 scripts/download.py --help >/dev/null
python3 scripts/benchmark.py --help >/dev/null
python3 scripts/analyze.py --help >/dev/null
python3 scripts/verify.py
python3 -m unittest discover -s tests -v
