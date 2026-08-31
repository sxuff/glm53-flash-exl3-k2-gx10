#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("manifests/glm53-exl3-k2.json"))
    parser.add_argument("--model-root", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    rows = []
    for item in manifest["files"]:
        path = args.model_root / item["path"]
        actual_bytes = path.stat().st_size if path.is_file() else None
        actual_hash = sha256(path) if actual_bytes == item["bytes"] else None
        rows.append({
            "path": item["path"],
            "expected_bytes": item["bytes"],
            "actual_bytes": actual_bytes,
            "expected_sha256": item["sha256"],
            "actual_sha256": actual_hash,
            "ok": actual_bytes == item["bytes"] and actual_hash == item["sha256"],
        })
    expected = {item["path"] for item in manifest["files"]}
    actual = {path.name for path in args.model_root.glob("model-*-of-*.safetensors")}
    report = {
        "repository": manifest["repository"],
        "revision": manifest["revision"],
        "expected_weight_shards": manifest["weight_shards"],
        "expected_weight_bytes": manifest["weight_bytes"],
        "verified_shards": sum(row["ok"] for row in rows),
        "verified_bytes": sum(row["actual_bytes"] or 0 for row in rows if row["ok"]),
        "missing_or_extra_shards": sorted(expected ^ actual),
        "all_hashes_verified": all(row["ok"] for row in rows) and actual == expected,
        "files": rows,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_hashes_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
