# GLM-5.3 Flash IQ2_XXS + native MTP on one DGX Spark

A pinned llama.cpp recipe for serving `unsloth/GLM-5.3-Flash-GGUF` UD-IQ2_XXS with native MTP speculative decoding on one NVIDIA GB10 system.

Native MTP n=2 is the default fast profile. No-MTP is retained as the measured control and operational fallback.

## Measured comparison

One fixed-order sweep used four deterministic text workloads per arm, one warm-up followed by one measured 400-token request for each workload. Both arms used the same artifact, llama.cpp commit, 8K context, Flash Attention, seed, and request settings.

| Mode | Mean server decode rate | Aggregate whole-request rate |
|---|---:|---:|
| No MTP | 18.40 tok/s | 18.17 tok/s |
| Native MTP n=2 | **27.67 tok/s** | **26.56 tok/s** |

- Mean server decode speedup: **1.50x**, or **+50.36%**
- Aggregate whole-request speedup: **1.46x**
- MTP draft acceptance across all eight warm-up and measured requests: **70.38%**
- Minimum host `MemAvailable`: **17.04 GiB no-MTP**, **13.82 GiB MTP**
- Service swap and host swap growth: **0 bytes in both measured arms**

`Mean server decode rate` is the arithmetic mean of llama.cpp's per-request generation rates. `Aggregate whole-request rate` is 1,600 generated tokens divided by summed request wall time, including prompt processing and first-token latency.

Per-workload rates and full card values are in [`CARD_VALUES.md`](CARD_VALUES.md). The compact result receipt is [`results/summary.json`](results/summary.json).

## Exact stack

- Target: `unsloth/GLM-5.3-Flash-GGUF` at `2975ab414d30340466d8c51533c6e91f0cca64c1`
- Variant: `UD-IQ2_XXS`, four text shards plus BF16 vision projector
- Verified artifact size: **103,008,962,080 bytes**, or **95.93 GiB**
- Runtime: `unslothai/llama.cpp` at `629b50552801912b3e2078f9799e4d77213197d7`
- Runtime patch: two metadata-name mappings for the rewritten text shard and projector
- Hardware: one NVIDIA DGX Spark or equivalent GB10, 128 GB unified memory
- Measured context allocation: 8,192 tokens, one slot

Exact artifact sizes and SHA-256 values are in [`manifests/target.json`](manifests/target.json). Runtime lineage is in [`manifests/runtime.json`](manifests/runtime.json).

## Download and verify

Install the Hugging Face CLI, then run:

```bash
python3 scripts/download.py \
  --destination "$HOME/models/GLM-5.3-Flash-UD-IQ2_XXS-2975ab41"
```

The downloader pins the Hub revision, resumes partial transfers, preserves a 10 GiB free-disk margin, installs the corrected first shard and projector filenames, and verifies all five files against their Git LFS SHA-256 OIDs.

## Build the exact runtime

```bash
./scripts/build_runtime.sh
```

The script fetches the pinned runtime commit, applies the exercised metadata patch, and builds `llama-server` and `llama-bench` for SM121 with CUDA 13.

## Serve

Default native MTP n=2 profile:

```bash
MODEL_DIR="$HOME/models/GLM-5.3-Flash-UD-IQ2_XXS-2975ab41" \
./scripts/serve.sh
```

No-MTP control:

```bash
MODE=no-mtp \
MODEL_DIR="$HOME/models/GLM-5.3-Flash-UD-IQ2_XXS-2975ab41" \
./scripts/serve.sh
```

The OpenAI-compatible endpoint binds to `http://127.0.0.1:8001/v1`. Set `MMPROJ` to the verified projector path when native image input is needed. The measured speed arms did not load the projector.

For a cgroup-enforced zero-swap launch, run the server through a user systemd unit with `MemorySwapMax=0` and monitor host `MemAvailable` separately.

## Reproduce the sweep

Start a fresh no-MTP server and collect its arm:

```bash
python3 scripts/benchmark.py \
  --arm no-mtp \
  --base-url http://127.0.0.1:8001 \
  --output local/no-mtp.json
```

Restart the server with native MTP n=2, then collect the second arm:

```bash
python3 scripts/benchmark.py \
  --arm mtp-n2 \
  --base-url http://127.0.0.1:8001 \
  --output local/mtp-n2.json
```

Generate a compact local summary:

```bash
python3 scripts/analyze.py \
  --baseline local/no-mtp.json \
  --treatment local/mtp-n2.json \
  --output local/summary.json
```

Raw responses and host-local traces stay under the ignored `local/` directory. The committed summary contains aggregate timing, acceptance, memory, and lineage fields only.

## Scope

This is one fixed-order, one-repetition operational sweep on one GB10. Rates apply to the pinned artifact, runtime, settings, and four included workloads. Context-depth behavior and other runtimes are separate experiments.

## Attribution and license

llama.cpp provides the runtime and native MTP implementation. Unsloth provides the exercised GGUF artifact and rewritten shard metadata. Z.ai provides GLM-5.3 Flash. Model weights are not included and retain their upstream terms. Repository scripts and documentation are MIT licensed.
