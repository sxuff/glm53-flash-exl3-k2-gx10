# Dependency boundary

This repository contains two independent deployment and validation lanes for GLM-5.3 Flash on one NVIDIA GB10.

## GGUF lane

The GGUF lane pins and builds:

- Runtime: https://github.com/unslothai/llama.cpp
- Commit: `629b50552801912b3e2078f9799e4d77213197d7`
- Model repository: `unsloth/GLM-5.3-Flash-GGUF`
- Model revision: `2975ab414d30340466d8c51533c6e91f0cca64c1`

The repository carries a two-line compatibility patch that maps the rewritten artifact's canonical text architecture and projector type to the names expected by the pinned runtime. The patch is stored in `gguf/patches/gguf-canonical-naming.patch`.

## EXL3 lane

The EXL3 lane pins and invokes the MIT-licensed upstream recipe:

- Repository: https://github.com/vcruz305/GLM-5.3-Flash-EXL3-K2-DGX-Spark-recipe
- Commit: `0b8dd0d6c7b186076f2e61d1b99a6289f8006c3c`
- Model repository: `vcruz305/GLM-5.3-Flash-EXL3-K2`
- Model revision: `ca0bcdae265f7df1e346c57a2b53b8b8f632ee0b`

## Licenses

Model weights are not redistributed. They remain subject to their model repositories' terms and the source GLM-5.3 Flash license.

llama.cpp, vLLM, ExLlamaV3, FlashInfer, PyTorch, Hugging Face tooling, the pinned EXL3 recipe, and their transitive dependencies retain their own licenses. This repository's MIT license applies only to the scripts, tests, patches, and notes authored here.

This project is independent and is not endorsed by the referenced projects or vendors.
