# Result-card values

## Recommended card

**Title**
GLM-5.3 Flash at 27.7 tok/s on one DGX Spark

**Subtitle**
GB10 · 128 GB unified memory · Unsloth UD-IQ2_XXS · llama.cpp native MTP n=2

**Left metric**
No MTP
**18.40 tok/s**
mean server decode

**Right metric**
Native MTP n=2
**27.67 tok/s**
mean server decode

**Primary delta**
**1.50x faster**
**+50.36%**

**Per-workload MTP rates**

- Prose: **21.98 tok/s**
- Structured: **33.05 tok/s**
- Code: **27.39 tok/s**
- Math: **28.26 tok/s**

**Control rates**

- Prose: **18.53 tok/s**
- Structured: **18.46 tok/s**
- Code: **18.44 tok/s**
- Math: **18.18 tok/s**

**MTP acceptance**
**70.38%**
1,865 / 2,650 proposed draft tokens accepted across warm-ups and measured requests

**Memory proof**
Minimum host `MemAvailable`: **13.82 GiB with MTP**
Service swap: **0 B**
Host swap growth: **0 B**

**Artifact**
`unsloth/GLM-5.3-Flash-GGUF` · `UD-IQ2_XXS`
**95.93 GiB** including BF16 projector

**Runtime**
`unslothai/llama.cpp` · `629b50552801912b3e2078f9799e4d77213197d7`

**Method footnote**
Four workloads, 400 generated tokens each, one measured request per workload after one warm-up. Temperature 0, seed 42, 8K context, Flash Attention, one slot. Tok/s is the arithmetic mean of llama.cpp's per-request decode rates.

**Secondary whole-request values**
No MTP: **18.17 tok/s**
MTP n=2: **26.56 tok/s**
Speedup: **1.46x**

**Repository footer**
`gguf/results/summary.json`

## Do not mix these clocks

- Use **18.40 → 27.67 tok/s** only with the label `mean server decode`.
- Use **18.17 → 26.56 tok/s** only with the label `aggregate whole-request`.
- Do not label the 33.05 tok/s structured-workload result as the four-workload average.
- Do not imply that the projector was resident during the measured speed sweep.
