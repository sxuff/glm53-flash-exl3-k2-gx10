#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> int:
    target = json.loads((ROOT / "manifests" / "target.json").read_text())
    runtime = json.loads((ROOT / "manifests" / "runtime.json").read_text())
    summary = json.loads((ROOT / "results" / "summary.json").read_text())

    if sum(item["bytes"] for item in target["files"]) != summary["artifact"]["bytes"]:
        fail("target byte total disagrees with summary")
    if len(target["files"]) != summary["artifact"]["files"]:
        fail("target file count disagrees with summary")
    if sha256(ROOT / runtime["patch"]) != runtime["patch_sha256"]:
        fail("runtime patch hash mismatch")

    no_mtp = summary["arms"]["no-mtp"]
    mtp = summary["arms"]["mtp-n2"]
    ratio = mtp["mean_server_decode_tokens_per_second"] / no_mtp["mean_server_decode_tokens_per_second"]
    if abs(ratio - summary["comparison"]["mean_server_decode_ratio"]) > 1e-12:
        fail("mean decode ratio mismatch")
    wall_ratio = mtp["aggregate_whole_request_tokens_per_second"] / no_mtp["aggregate_whole_request_tokens_per_second"]
    if abs(wall_ratio - summary["comparison"]["aggregate_whole_request_ratio"]) > 1e-12:
        fail("whole-request ratio mismatch")
    acceptance = mtp["acceptance"]
    if abs(acceptance["accepted_draft_tokens"] / acceptance["proposed_draft_tokens"] - acceptance["rate"]) > 1e-12:
        fail("acceptance mismatch")

    for arm in (no_mtp, mtp):
        if arm["minimum_mem_available_bytes"] <= 6 * 1024**3:
            fail("memory reserve failed")
        if arm["maximum_host_swap_growth_bytes"] != 0:
            fail("host swap growth is not zero")
        if arm["maximum_service_swap_bytes"] != 0:
            fail("service swap is not zero")

    docs = "\n".join((ROOT / name).read_text() for name in ("README.md", "REPORT.md", "CARD_VALUES.md"))
    if "quality" in docs.lower():
        fail("public narrative contains excluded framing")

    private_literals = [
        "s" + "xuf",
        "gx10" + "-fe09",
        "/home/" + "sx" + "uf",
        "100." + "64.",
    ]
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        data = path.read_bytes()
        for literal in private_literals:
            if literal.encode() in data:
                fail(f"private literal found in {path.relative_to(ROOT)}")

    markdown = [ROOT / "README.md", ROOT / "REPORT.md", ROOT / "CARD_VALUES.md"]
    link_pattern = re.compile(r"\[[^]]+\]\((?!https?://|#)([^)]+)\)")
    for path in markdown:
        for link in link_pattern.findall(path.read_text()):
            if not (path.parent / link).resolve().exists():
                fail(f"broken relative link in {path.name}: {link}")

    serve = (ROOT / "scripts" / "serve.sh").read_text()
    for token in ('MODE="${MODE:-mtp}"', "--spec-type draft-mtp", "--spec-draft-n-max 2", "--spec-draft-n-min 0", "--host \"$HOST\""):
        if token not in serve:
            fail(f"serve contract missing: {token}")

    print(json.dumps({
        "status": "passed",
        "target_files": len(target["files"]),
        "target_bytes": sum(item["bytes"] for item in target["files"]),
        "runtime_commit": runtime["commit"],
        "mean_decode_ratio": ratio,
        "acceptance_rate": acceptance["rate"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
