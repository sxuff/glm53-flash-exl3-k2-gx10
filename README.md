# GLM-5.3-Flash EXL3 K2 on one NVIDIA GB10

A pinned, checksum-verified recipe for serving [`vcruz305/GLM-5.3-Flash-EXL3-K2`](https://huggingface.co/vcruz305/GLM-5.3-Flash-EXL3-K2) on one NVIDIA DGX Spark or ASUS Ascent GX10 with native MTP k=2.

This repository contains deployment scripts, tests, and measured receipts. It does not contain model weights or runtime wheels. It pins and invokes the upstream recipe instead of repackaging that runtime. See [`NOTICE.md`](NOTICE.md).

## Verified stack

- Hardware: one NVIDIA GB10, 128 GB unified memory, `aarch64`, SM121
- Model: `vcruz305/GLM-5.3-Flash-EXL3-K2`
- Model revision: `ca0bcdae265f7df1e346c57a2b53b8b8f632ee0b`
- Artifact: 120 safetensors shards, 97,728,721,536 bytes (91.017 GiB), 120/120 SHA-256 verified
- Quantization: EXL3 K2, 2-bit MCG routed experts; attention, shared experts, embeddings, LM head, and vision remain native BF16
- Upstream recipe: `vcruz305/GLM-5.3-Flash-EXL3-K2-DGX-Spark-recipe` at `0b8dd0d6c7b186076f2e61d1b99a6289f8006c3c`
- Runtime: vLLM `878631b6079d2cf9fb80830ef9cb41b43aded098`, version `0.1.dev62+g878631b60.d20260830`
- Kernels: ExLlamaV3 `17bc3923259ffd48aab742edd261a0ca45d55459`, FlashInfer `0.6.18rc10`
- Framework: PyTorch `2.13.0+cu130`, Python 3.12
- Serving profile: one 65,536-token slot, FP8 KV, fused `exl3_moe`, native MTP k=2, `GPU_MEM_UTIL=0.87`
- API: OpenAI-compatible vLLM server on `127.0.0.1:8888`

Stock vLLM cannot load this artifact. The EXL3 quantization method, Glm5Next architecture, sparse-MLA fixes, and fused routed-expert kernel come from the pinned runtime above.

## 1. Preflight the GB10 host

Run on the GB10 host, not inside a management container:

```bash
uname -m
python3.12 --version
nvidia-smi
/usr/local/cuda-13.0/bin/nvcc --version
free -h
```

`uname -m` must report `aarch64`. Install Python's matching development headers before runtime installation because Triton or a transitive native dependency may compile a helper:

```bash
sudo apt-get update
sudo apt-get install -y git python3.12 python3.12-venv python3.12-dev
```

Keep at least 6 GiB `MemAvailable`. Stop the owned service if service swap becomes nonzero or whole-host swap grows by more than 512 MiB from the pre-launch baseline.

## 2. Install the pinned runtime

```bash
bash scripts/bootstrap_runtime.sh
```

The bootstrap script fetches the exact upstream commit, verifies `FETCH_HEAD`, installs the prebuilt ARM64/CUDA 13 runtime into `~/venvs/glm53-exl3-local`, and runs the upstream preflight. It never installs stock `vllm` from PyPI.

A cold load of the 91 GiB checkpoint takes roughly 11 minutes. Quiet logs during that interval are not evidence of a hang.

## 3. Download and verify the exact artifact

The manifest records every shard's exact byte size and SHA-256.

```bash
source ~/venvs/glm53-exl3-local/bin/activate
bash scripts/download_model.sh
```

Verify an existing model directory without downloading:

```bash
python3 scripts/verify_model.py \
  --manifest manifests/glm53-exl3-k2.json \
  --model-root "$HOME/models/GLM-5.3-Flash-EXL3-K2"
```

The verifier passes only when all 120 expected shards are present and all 120 content hashes match.

## 4. Install the localhost service

```bash
bash scripts/install_service.sh
systemctl --user enable --now glm53-exl3-k2.service
journalctl --user -u glm53-exl3-k2.service -f
```

The installed profile is:

```text
HOST=127.0.0.1
PORT=8888
SPEC_METHOD=mtp
MTP_TOKENS=2
MAX_MODEL_LEN=65536
MAX_NUM_SEQS=1
MAX_NUM_BATCHED_TOKENS=2048
GPU_MEM_UTIL=0.87
EXL3_FUSED_MOE=1
```

The unit applies:

```text
MemoryHigh=108G
MemoryMax=112G
MemorySwapMax=0
```

## 5. Exercise text, tools, and native vision

```bash
python3 scripts/smoke.py --base-url http://127.0.0.1:8888
```

The retained validation receipt passed 9/9 checks: model identity, exact text, two distinct prefill requests, 1K-input/256-output generation, structured tool calling, thinking mode, a generated image, and a realistic screenshot. Native vision passed 2/2 image checks. See [`results/functional-validation.json`](results/functional-validation.json).

## Measured native MTP k=2 operating sweep

One four-case sweep on the verified 64K single-slot service. Each case used one warm-up plus one measured request, temperature 0, top-p 1, seed 42, thinking disabled, and exactly 400 generated tokens with `finish_reason: length`.

`Decode tok/s` is server generation tokens divided by the server's request decode time. It excludes prefill and TTFT.

| Case | Output tokens | Decode tok/s | MTP drafts accepted | Verified tokens/step |
|---|---:|---:|---:|---:|
| Prose | 400 | 13.2363 | 46.39% | 1.9279 |
| Structured sequence | 400 | 20.2586 | 97.06% | 2.9412 |
| Code | 400 | 16.9598 | 72.39% | 2.4479 |
| Math | 400 | 14.9849 | 59.89% | 2.1978 |
| **Aggregate** | **1,600** | **15.9612** | **66.11%** | **2.3222** |

Across the measured requests, MTP accepted 911 of 1,378 proposed tokens. Minimum host `MemAvailable` was 9,771,429,888 bytes (9.100 GiB), host swap did not grow, and service swap stayed at 0 bytes.

This is one bounded operating sweep, not a broad model benchmark. No matched no-spec speedup is claimed. Full denominators, per-request hashes, runtime identity, acceptance counters, timings, and safety telemetry are in [`results/mtp-k2.json`](results/mtp-k2.json).

Reproduce it against the loaded MTP service:

```bash
python3 scripts/benchmark_mtp.py \
  --base-url http://127.0.0.1:8888 \
  --output results/raw/mtp-k2.json
```

## Artifact and safety receipts

- Artifact: 120/120 shards and 97,728,721,536/97,728,721,536 bytes SHA-256 verified
- Guarded startup: 661.72 seconds, 0 bytes service swap, 148,135,936 bytes maximum host-swap growth
- Functional validation: 9/9 checks, including 2/2 native-vision checks
- Benchmark: 1,600 measured completion tokens, 0 bytes service swap, 0 bytes host-swap growth

Machine-readable summaries:

- [`results/artifact-verification.json`](results/artifact-verification.json)
- [`results/functional-validation.json`](results/functional-validation.json)
- [`results/mtp-k2.json`](results/mtp-k2.json)

## Quality boundary

This is an aggressive 2-bit routed-expert quant, not BF16 quality. The upstream recipe reports token-mean KLD 0.3346 and 78.8% top-1 agreement against BF16 on its sealed fidelity corpus. Treat rare long-task derailments as possible and keep public claims scoped to the exact tested artifact and checks.

## Safety and troubleshooting

Inspect the owned service before changing context, memory utilization, sequence count, or speculation depth:

```bash
systemctl --user status glm53-exl3-k2.service --no-pager
systemctl --user show glm53-exl3-k2.service \
  -p MemoryCurrent -p MemorySwapCurrent -p MemoryHigh -p MemoryMax -p MemorySwapMax
awk '/MemAvailable|SwapTotal|SwapFree/ {print}' /proc/meminfo
nvidia-smi
```

Common failures:

- `quantization method exl3 is not supported`: stock vLLM was installed. Re-run the pinned bootstrap.
- `Python.h: No such file or directory`: install `python3.12-dev` or provide matching local headers through `CPATH`.
- `No valid attention backend ... FLASHINFER_MLA_SPARSE_SM120`: put CUDA 13 `nvcc` and the runtime venv's `ninja` on `PATH`.
- Model appears idle during startup: allow roughly 11 minutes for the 91 GiB load before diagnosing a hang.
- Long HTML or source generation appears frozen: inspect request progress and output budget. At roughly 16 tok/s, thousands of output tokens take minutes.

## Cleanup

```bash
systemctl --user disable --now glm53-exl3-k2.service
rm -f "$HOME/.config/systemd/user/glm53-exl3-k2.service"
systemctl --user daemon-reload
```

Cleanup intentionally leaves the model, runtime venv, and pinned upstream source tree in place.

## License and attribution

The scripts and notes authored here are MIT licensed. The model weights are not redistributed and retain their own license. The pinned upstream runtime recipe is separately MIT licensed. See [`NOTICE.md`](NOTICE.md) for the exact dependency boundary.
