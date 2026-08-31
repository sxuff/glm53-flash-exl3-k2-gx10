#!/usr/bin/env python3
"""Bounded native-MTP operating sweep for GLM-5.3-Flash EXL3 K2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import urllib.request

GIB = 1024**3
PROMPTS = {
    "prose": (
        "Write a self-contained technical explanation of how unified CPU/GPU memory changes "
        "large-language-model inference on a single workstation. Use complete paragraphs, "
        "include benefits and bottlenecks, and do not use a table. Continue for at least 500 tokens."
    ),
    "structured": (
        "Output the integers from 1 through 260 in order. Put exactly one space between integers. "
        "Do not omit, repeat, explain, or add any other text."
    ),
    "code": (
        "Implement a production-quality Python module that parses a stream of Server-Sent Events "
        "from an iterable of bytes, yields decoded JSON data objects, handles comments and multi-line "
        "data fields, and stops on [DONE]. Include type hints, a docstring, validation, and focused "
        "unit tests. Continue until the implementation and tests are complete."
    ),
    "math": (
        "Solve this carefully and show the full derivation: a decoder produces one verified token per "
        "base-model step without speculation. A speculative method proposes k tokens; position i is "
        "accepted only if all earlier positions were accepted. Derive expected verified tokens per "
        "step from conditional acceptance probabilities, then evaluate k=4 for p=[0.82,0.61,0.40,0.20]. "
        "Discuss proposal overhead, the break-even condition, and two numerical edge cases in at least "
        "500 tokens."
    ),
}
METRIC = re.compile(r"^([^\s{]+)(\{[^}]*\})?\s+([-+0-9.eE]+)$")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def request_bytes(url: str, payload: dict | None = None, timeout: int = 60) -> bytes:
    body = None if payload is None else canonical(payload)
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        return response.read()


def request_json(url: str, payload: dict | None = None, timeout: int = 60) -> dict:
    result = json.loads(request_bytes(url, payload, timeout))
    if not isinstance(result, dict):
        raise RuntimeError(f"{url} did not return a JSON object")
    return result


def metrics(url: str) -> dict[str, float]:
    text = request_bytes(url, timeout=30).decode("utf-8", "replace")
    out: dict[str, float] = {}
    for line in text.splitlines():
        match = METRIC.match(line.strip())
        if match:
            try:
                out[match.group(1) + (match.group(2) or "")] = float(match.group(3))
            except ValueError:
                pass
    return out


def metric_total(snapshot: dict[str, float], name: str) -> float:
    return sum(value for key, value in snapshot.items() if key == name or key.startswith(name + "{"))


def metric_delta(before: dict[str, float], after: dict[str, float], name: str) -> float:
    return metric_total(after, name) - metric_total(before, name)


def mem_available() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable missing")


def swap_used() -> int:
    rows = Path("/proc/swaps").read_text().splitlines()[1:]
    return sum(int(row.split()[3]) * 1024 for row in rows if row.split())


def service_swap(unit: str) -> int:
    output = subprocess.check_output(
        ["systemctl", "--user", "show", unit, "-p", "ControlGroup"], text=True
    ).strip()
    group = output.split("=", 1)[1] if "=" in output else ""
    path = Path("/sys/fs/cgroup") / group.lstrip("/") / "memory.swap.current"
    return int(path.read_text()) if path.is_file() else 0


def stream_request(url: str, payload: dict, timeout: int) -> dict:
    request_body = canonical(payload)
    req = urllib.request.Request(
        url,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    first_content = None
    parts: list[str] = []
    usage: dict = {}
    finish_reason = None
    system_fingerprint = None
    response_id = None
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"completion returned HTTP {response.status}")
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            event = json.loads(data)
            system_fingerprint = event.get("system_fingerprint") or system_fingerprint
            response_id = event.get("id") or response_id
            if event.get("usage"):
                usage = event["usage"]
            for choice in event.get("choices") or []:
                if choice.get("finish_reason") is not None:
                    finish_reason = choice["finish_reason"]
                content = (choice.get("delta") or {}).get("content") or ""
                if content:
                    if first_content is None:
                        first_content = time.perf_counter()
                    parts.append(content)
    finished = time.perf_counter()
    content = "".join(parts)
    return {
        "request_sha256": hashlib.sha256(request_body).hexdigest(),
        "response_id": response_id,
        "system_fingerprint": system_fingerprint,
        "usage": usage,
        "finish_reason": finish_reason,
        "wall_seconds": finished - started,
        "ttft_seconds": (first_content or finished) - started,
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "content_chars": len(content),
        "content_head": content[:160],
        "content_tail": content[-160:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", default="mtp-k2", choices=("mtp-k2",))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8888")
    parser.add_argument("--model", default="glm53-flash-exl3-k2")
    parser.add_argument("--unit", default="glm53-exl3-k2.service")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=400)
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    if args.warmup < 0 or args.runs != 1 or args.max_tokens < 2:
        parser.error("public recipe expects --warmup >= 0, --runs 1, --max-tokens >= 2")

    base = args.base_url.rstrip("/")
    models = request_json(base + "/v1/models", timeout=30)
    model_rows = models.get("data") or []
    model_row = next((row for row in model_rows if row.get("id") == args.model), None)
    if not model_row or model_row.get("max_model_len") != 65536:
        raise SystemExit(f"model identity/context mismatch: {models}")
    version = request_json(base + "/version", timeout=30)

    baseline_swap = swap_used()
    telemetry = {
        "minimum_mem_available_bytes": mem_available(),
        "maximum_host_swap_growth_bytes": 0,
        "maximum_service_swap_bytes": 0,
        "samples": 0,
        "breach": None,
    }
    stop = threading.Event()

    def monitor() -> None:
        while not stop.wait(0.5):
            available = mem_available()
            host_growth = max(0, swap_used() - baseline_swap)
            owned_swap = service_swap(args.unit)
            telemetry["minimum_mem_available_bytes"] = min(
                telemetry["minimum_mem_available_bytes"], available
            )
            telemetry["maximum_host_swap_growth_bytes"] = max(
                telemetry["maximum_host_swap_growth_bytes"], host_growth
            )
            telemetry["maximum_service_swap_bytes"] = max(
                telemetry["maximum_service_swap_bytes"], owned_swap
            )
            telemetry["samples"] += 1
            if available < 6 * GIB:
                telemetry["breach"] = f"MemAvailable below 6 GiB: {available}"
            elif host_growth > 512 * 1024**2:
                telemetry["breach"] = f"host swap growth above 512 MiB: {host_growth}"
            elif owned_swap > 0:
                telemetry["breach"] = f"service swap nonzero: {owned_swap}"
            if telemetry["breach"]:
                subprocess.run(["systemctl", "--user", "stop", args.unit], check=False)
                stop.set()
                return

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    warmups = []
    rows = []
    status = "failed"
    failure = None
    try:
        for case_name, prompt in PROMPTS.items():
            payload = {
                "model": args.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "top_p": 1.0,
                "seed": 42,
                "max_tokens": args.max_tokens,
                "ignore_eos": True,
                "stream": True,
                "stream_options": {"include_usage": True},
                "chat_template_kwargs": {"enable_thinking": False},
            }
            for ordinal in range(args.warmup + args.runs):
                is_warmup = ordinal < args.warmup
                before = metrics(base + "/metrics")
                record = stream_request(base + "/v1/chat/completions", payload, args.timeout)
                after = metrics(base + "/metrics")
                generated = metric_delta(before, after, "vllm:generation_tokens_total")
                decode_seconds = metric_delta(before, after, "vllm:request_decode_time_seconds_sum")
                drafts = metric_delta(before, after, "vllm:spec_decode_num_drafts_total")
                proposed = metric_delta(before, after, "vllm:spec_decode_num_draft_tokens_total")
                accepted = metric_delta(before, after, "vllm:spec_decode_num_accepted_tokens_total")
                record.update({
                    "case": case_name,
                    "warmup": is_warmup,
                    "run": ordinal + 1 if is_warmup else ordinal - args.warmup + 1,
                    "server_generation_tokens": generated,
                    "server_decode_seconds": decode_seconds,
                    "server_decode_tokens_per_second": generated / decode_seconds if decode_seconds > 0 else None,
                    "mtp_draft_steps": drafts,
                    "mtp_proposed_tokens": proposed,
                    "mtp_accepted_tokens": accepted,
                    "mtp_acceptance_rate": accepted / proposed if proposed > 0 else None,
                    "mtp_verified_tokens_per_step": 1 + accepted / drafts if drafts > 0 else None,
                })
                completion_tokens = int(record["usage"].get("completion_tokens") or 0)
                if completion_tokens != args.max_tokens or record["finish_reason"] != "length":
                    raise RuntimeError(
                        f"{case_name} denominator mismatch: tokens={completion_tokens} finish={record['finish_reason']}"
                    )
                if round(generated) != completion_tokens:
                    raise RuntimeError(
                        f"{case_name} server/client token mismatch: server={generated} client={completion_tokens}"
                    )
                (warmups if is_warmup else rows).append(record)
                if telemetry["breach"]:
                    raise RuntimeError(telemetry["breach"])
        total_proposed = sum(float(row["mtp_proposed_tokens"]) for row in rows)
        if total_proposed <= 0:
            raise RuntimeError("MTP treatment produced no draft tokens")
        status = "passed"
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        stop.set()
        thread.join(timeout=5)

    result = {
        "schema_version": 1,
        "status": status,
        "failure": failure,
        "arm": args.arm,
        "design": {
            "cases": list(PROMPTS),
            "warmups_per_case": args.warmup,
            "measured_runs_per_case": args.runs,
            "completion_tokens_per_request": args.max_tokens,
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 42,
            "thinking": False,
            "context_tokens": 65536,
            "max_num_seqs": 1,
        },
        "model": model_row,
        "runtime": version,
        "telemetry": telemetry,
        "warmups": warmups,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": status,
        "failure": failure,
        "arm": args.arm,
        "rows": len(rows),
        "completion_tokens": sum(int(row["usage"]["completion_tokens"]) for row in rows),
        "telemetry": telemetry,
        "output": os.fspath(args.output),
    }, indent=2, sort_keys=True))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
