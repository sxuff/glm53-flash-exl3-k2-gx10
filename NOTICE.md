# Dependency boundary

This repository is an independent deployment and validation recipe.

It pins and invokes the MIT-licensed upstream recipe:

- Repository: https://github.com/vcruz305/GLM-5.3-Flash-EXL3-K2-DGX-Spark-recipe
- Commit: `0b8dd0d6c7b186076f2e61d1b99a6289f8006c3c`

The model weights are not redistributed. They are downloaded from
`vcruz305/GLM-5.3-Flash-EXL3-K2` at the immutable revision recorded in the
manifest and remain subject to the model's own license and the source
GLM-5.3-Flash license.

vLLM, ExLlamaV3, FlashInfer, PyTorch, Hugging Face tooling, and their transitive
dependencies retain their own licenses. This repository's MIT license applies
only to the scripts, tests, and notes authored here.

This project is independent and is not endorsed by the referenced projects or
vendors.
