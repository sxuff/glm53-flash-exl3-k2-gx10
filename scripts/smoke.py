#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import struct
import urllib.request
import zlib


def png_red(width: int = 32, height: int = 32) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def call(url: str, payload: dict | None = None, timeout: int = 300) -> tuple[int, bytes]:
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8888")
    parser.add_argument("--model", default="glm53-flash-exl3-k2")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    health_status, _ = call(base + "/health", timeout=30)
    _, raw_models = call(base + "/v1/models", timeout=30)
    models = json.loads(raw_models)
    identity = next((row for row in models.get("data", []) if row.get("id") == args.model), None)
    if health_status != 200 or not identity or identity.get("max_model_len") != 65536:
        raise SystemExit("health or model identity failed")

    common = {"model": args.model, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}}
    payload = {**common, "messages": [{"role": "user", "content": "Reply with exactly: GB10 READY"}], "max_tokens": 16}
    _, raw_text = call(base + "/v1/chat/completions", payload)
    text = json.loads(raw_text)
    text_content = text["choices"][0]["message"].get("content") or ""
    text_ok = "GB10 READY" in text_content

    tools = [{"type": "function", "function": {"name": "lookup_inventory", "description": "Look up one SKU", "parameters": {"type": "object", "properties": {"sku": {"type": "string"}}, "required": ["sku"]}}}]
    payload = {**common, "messages": [{"role": "user", "content": "Call lookup_inventory for SKU GX10."}], "max_tokens": 96, "tools": tools, "tool_choice": "required"}
    _, raw_tool = call(base + "/v1/chat/completions", payload)
    tool = json.loads(raw_tool)
    calls = tool["choices"][0]["message"].get("tool_calls") or []
    tool_ok = bool(calls and calls[0]["function"].get("name") == "lookup_inventory" and json.loads(calls[0]["function"].get("arguments") or "{}").get("sku") == "GX10")

    image = "data:image/png;base64," + base64.b64encode(png_red()).decode()
    payload = {**common, "messages": [{"role": "user", "content": [{"type": "text", "text": "What single color fills this image? Reply with one lowercase word."}, {"type": "image_url", "image_url": {"url": image}}]}], "max_tokens": 16}
    _, raw_vision = call(base + "/v1/chat/completions", payload)
    vision = json.loads(raw_vision)
    vision_content = vision["choices"][0]["message"].get("content") or ""
    vision_ok = "red" in vision_content.lower()

    result = {
        "health_http_status": health_status,
        "model": identity,
        "text": {"passed": text_ok, "output": text_content, "usage": text.get("usage")},
        "tool_call": {"passed": tool_ok, "tool_calls": calls, "usage": tool.get("usage")},
        "native_vision": {"passed": vision_ok, "output": vision_content, "usage": vision.get("usage")},
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if text_ok and tool_ok and vision_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
