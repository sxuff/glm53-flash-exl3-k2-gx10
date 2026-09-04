#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

GIB = 1024**3
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "target.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(path: Path, item: dict) -> dict:
    actual_bytes = path.stat().st_size if path.is_file() else None
    actual_hash = sha256(path) if actual_bytes == item["bytes"] else None
    return {
        "name": item["final_name"],
        "actual_bytes": actual_bytes,
        "expected_bytes": item["bytes"],
        "actual_sha256": actual_hash,
        "expected_sha256": item["sha256"],
        "ok": actual_bytes == item["bytes"] and actual_hash == item["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and verify the pinned GLM-5.3 Flash IQ2_XXS artifact")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--reserve-gib", type=int, default=10)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    destination = args.destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    report_path = args.report or destination / "verification.json"

    final_rows = [inspect(destination / item["final_name"], item) for item in manifest["files"]]
    missing = [item for item, row in zip(manifest["files"], final_rows) if not row["ok"]]

    for item, row in zip(manifest["files"], final_rows):
        final = destination / item["final_name"]
        if final.exists() and not row["ok"]:
            raise RuntimeError(f"refusing to overwrite invalid final file: {final}")

    if missing:
        required = sum(item["bytes"] for item in missing) + args.reserve_gib * GIB
        available = shutil.disk_usage(destination).free
        print(json.dumps({"available_bytes": available, "required_bytes": required, "margin_bytes": available - required}))
        if available < required:
            raise RuntimeError(f"disk reserve gate failed: available={available} required={required}")

        command = [
            "hf", "download", manifest["repository"],
            "--revision", manifest["revision"],
            "--local-dir", os.fspath(destination),
        ]
        for item in missing:
            command.extend(["--include", item["source_path"]])
        subprocess.run(command, check=True)

        staged = []
        for item in missing:
            source = destination / item["source_path"]
            row = inspect(source, {**item, "final_name": item["source_path"]})
            staged.append(row)
        if not all(row["ok"] for row in staged):
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps({"status": "staging_failed", "files": staged}, indent=2, sort_keys=True) + "\n")
            return 1

        for item in missing:
            os.replace(destination / item["source_path"], destination / item["final_name"])

    rows = [inspect(destination / item["final_name"], item) for item in manifest["files"]]
    report = {
        "schema_version": 1,
        "status": "passed" if all(row["ok"] for row in rows) else "failed",
        "repository": manifest["repository"],
        "revision": manifest["revision"],
        "variant": manifest["variant"],
        "verified_files": sum(row["ok"] for row in rows),
        "verified_bytes": sum((row["actual_bytes"] or 0) for row in rows if row["ok"]),
        "free_bytes_after": shutil.disk_usage(destination).free,
        "files": rows,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "repository", "revision", "variant", "verified_files", "verified_bytes", "free_bytes_after")}, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
