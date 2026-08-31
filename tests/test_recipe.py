#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_REVISION = "ca0bcdae265f7df1e346c57a2b53b8b8f632ee0b"
UPSTREAM_COMMIT = "0b8dd0d6c7b186076f2e61d1b99a6289f8006c3c"
VLLM_COMMIT = "878631b6079d2cf9fb80830ef9cb41b43aded098"

manifest = json.loads((ROOT / "manifests/glm53-exl3-k2.json").read_text())
assert manifest["repository"] == "vcruz305/GLM-5.3-Flash-EXL3-K2"
assert manifest["revision"] == MODEL_REVISION
assert manifest["weight_shards"] == len(manifest["files"]) == 120
assert manifest["weight_bytes"] == sum(row["bytes"] for row in manifest["files"]) == 97_728_721_536
assert all(len(row["sha256"]) == 64 for row in manifest["files"])
assert len({row["path"] for row in manifest["files"]}) == 120

artifact = json.loads((ROOT / "results/artifact-verification.json").read_text())
assert artifact["status"] == "passed"
assert artifact["resolved_revision"] == MODEL_REVISION
assert artifact["weight_shards_verified"] == artifact["weight_shards_total"] == 120
assert artifact["weight_bytes_verified"] == artifact["weight_bytes_total"] == 97_728_721_536
assert artifact["all_sha256_verified"] is True

functional = json.loads((ROOT / "results/functional-validation.json").read_text())
assert functional["status"] == "passed"
assert functional["summary"]["passed"] == functional["summary"]["total"] == 9
assert functional["summary"]["native_vision_passed"] == functional["summary"]["native_vision_total"] == 2
assert functional["safety"]["maximum_service_swap_bytes"] == 0
assert functional["safety"]["breach"] is None

benchmark = json.loads((ROOT / "results/mtp-k2.json").read_text())
assert benchmark["status"] == "passed"
assert benchmark["model"]["revision"] == MODEL_REVISION
assert benchmark["runtime"]["version"].startswith("0.1.dev62+g878631b60")
assert benchmark["design"]["measured_cases"] == 4
assert benchmark["design"]["repetitions"] == 1
assert benchmark["design"]["completion_tokens_per_request"] == 400
assert benchmark["aggregate"]["completion_tokens"] == 1600
assert benchmark["aggregate"]["mtp_proposed_tokens"] > 0
assert benchmark["aggregate"]["mtp_accepted_tokens"] > 0
assert benchmark["safety"]["maximum_service_swap_bytes"] == 0
assert benchmark["safety"]["breach"] is None
assert all(row["output_tokens"] == 400 for row in benchmark["cases"])

readme = (ROOT / "README.md").read_text()
bootstrap = (ROOT / "scripts/bootstrap_runtime.sh").read_text()
launcher = (ROOT / "scripts/run_server.sh").read_text()
service = (ROOT / "systemd/glm53-exl3-k2.service").read_text()
for value in (MODEL_REVISION, UPSTREAM_COMMIT, VLLM_COMMIT, "97,728,721,536", "SM121"):
    assert value in readme or value in bootstrap
for value in ("15.9612", "66.11%", "13.2363", "20.2586", "16.9598", "14.9849", "No matched no-spec speedup is claimed"):
    assert value in readme
for value in ("127.0.0.1", "MAX_MODEL_LEN", "65536", "SPEC_METHOD", "MTP_TOKENS", "GPU_MEM_UTIL", "0.87", "EXL3_FUSED_MOE"):
    assert value in launcher
assert "MemorySwapMax=0" in service
assert "MemoryHigh=108G" in service
assert "MemoryMax=112G" in service

all_public_text = "\n".join(
    path.read_text(errors="replace")
    for path in ROOT.rglob("*")
    if path.is_file() and "__pycache__" not in path.parts and "raw" not in path.parts
)
for forbidden in (
    "/home/" + "sxuf",
    "gx10" + "-fe09",
    "proxy" + ".key",
    "api" + "_key=",
    "Authorization: " + "Bearer",
    "cache/" + "images",
    "0x" + "Sero",
    "Victor " + "Cruz",
):
    assert forbidden not in all_public_text

print("recipe tests passed")
