#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize(data: dict) -> dict:
    if data.get("status") != "passed" or len(data.get("rows", [])) != 4:
        raise ValueError(f"arm is incomplete: {data.get('arm')}")
    rows = data["rows"]
    all_rows = data.get("warmups", []) + rows
    completion_tokens = sum(int(row["completion_tokens"]) for row in rows)
    wall_seconds = sum(float(row["wall_seconds"]) for row in rows)
    proposed = sum(int(row.get("draft_tokens") or 0) for row in all_rows)
    accepted = sum(int(row.get("accepted_draft_tokens") or 0) for row in all_rows)
    return {
        "mean_server_decode_tokens_per_second": sum(float(row["server_decode_tokens_per_second"]) for row in rows) / len(rows),
        "aggregate_whole_request_tokens_per_second": completion_tokens / wall_seconds,
        "summed_wall_seconds": wall_seconds,
        "measured_completion_tokens": completion_tokens,
        "minimum_mem_available_bytes": data["telemetry"]["minimum_mem_available_bytes"],
        "maximum_host_swap_growth_bytes": data["telemetry"]["maximum_host_swap_growth_bytes"],
        "maximum_service_swap_bytes": data["telemetry"]["maximum_service_swap_bytes"],
        "per_workload_server_decode_tokens_per_second": {row["case"]: row["server_decode_tokens_per_second"] for row in rows},
        "acceptance": {
            "scope": "warm-up plus measured requests",
            "proposed_draft_tokens": proposed,
            "accepted_draft_tokens": accepted,
            "rate": accepted / proposed if proposed else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact GLM-5.3 Flash MTP speed summary")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--treatment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text())
    treatment = json.loads(args.treatment.read_text())
    base_rows = {row["case"]: row for row in baseline["rows"]}
    treatment_rows = {row["case"]: row for row in treatment["rows"]}
    if set(base_rows) != set(treatment_rows):
        raise SystemExit("workload sets differ")
    if any(base_rows[key]["request_sha256"] != treatment_rows[key]["request_sha256"] for key in base_rows):
        raise SystemExit("request payloads differ")

    base_summary = summarize(baseline)
    treatment_summary = summarize(treatment)
    result = {
        "schema_version": 1,
        "protocol": {
            "workloads": len(base_rows),
            "order": list(base_rows),
            "matched_request_payloads": len(base_rows),
        },
        "arms": {"no-mtp": base_summary, "mtp-n2": treatment_summary},
        "comparison": {
            "mean_server_decode_ratio": treatment_summary["mean_server_decode_tokens_per_second"] / base_summary["mean_server_decode_tokens_per_second"],
            "mean_server_decode_increase_percent": (treatment_summary["mean_server_decode_tokens_per_second"] / base_summary["mean_server_decode_tokens_per_second"] - 1) * 100,
            "aggregate_whole_request_ratio": treatment_summary["aggregate_whole_request_tokens_per_second"] / base_summary["aggregate_whole_request_tokens_per_second"],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
