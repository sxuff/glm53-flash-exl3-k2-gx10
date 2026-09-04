# GLM-5.3 Flash native MTP result

## Result

On one NVIDIA GB10, native MTP n=2 increased the four-workload mean llama.cpp decode rate from **18.4016320415 tok/s** to **27.6690014301 tok/s**.

- Ratio: **1.5036167101x**
- Increase: **50.3616710069%**
- Aggregate whole-request rate: **18.1711492711 → 26.5628981993 tok/s**
- Aggregate whole-request ratio: **1.4618171808x**

## Per-workload server decode

| Workload | No MTP | MTP n=2 | Increase |
|---|---:|---:|---:|
| Prose | 18.5305187194 | 21.9776793807 | 18.6026128762% |
| Structured | 18.4590154803 | 33.0479612887 | 79.0342574007% |
| Code | 18.4376609974 | 27.3878949623 | 48.5432179610% |
| Math | 18.1793329688 | 28.2624700889 | 55.4648354664% |

## MTP telemetry

Across four warm-ups and four measured requests:

- Proposed draft tokens: **2,650**
- Accepted draft tokens: **1,865**
- Overall acceptance: **70.3773584906%**
- First proposal position: **1,062 / 1,325**, or **80.1509433962%**
- Second proposal position: **803 / 1,325**, or **60.6037735849%**

## Safety telemetry

| Arm | Minimum host MemAvailable | Host swap growth | Service swap |
|---|---:|---:|---:|
| No MTP | 18,300,747,776 bytes | 0 bytes | 0 bytes |
| MTP n=2 | 14,842,114,048 bytes | 0 bytes | 0 bytes |

Both arms stayed above the frozen 6 GiB host-memory reserve.

## Measurement contract

- Hardware: one NVIDIA GB10 with 128 GB unified memory
- Target: Unsloth GLM-5.3 Flash UD-IQ2_XXS
- Runtime: `unslothai/llama.cpp` commit `629b50552801912b3e2078f9799e4d77213197d7`
- Context allocation: 8,192 tokens
- Parallel slots: one
- Flash Attention: enabled
- MTP treatment: `--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 0`
- Requests: four workload families, fixed order
- Repetitions: one warm-up plus one measured request per workload and arm
- Generation: 400 tokens, temperature 0, top-p 1, seed 42, EOS ignored

The committed public receipt omits prompts, generated text, host paths, and raw service metadata. Source artifact hashes remain in `manifests/target.json`.
