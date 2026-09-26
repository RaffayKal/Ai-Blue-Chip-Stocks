#!/usr/bin/env python3
"""Verify the configured pod's health, authentication, and real inference."""

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    config = json.loads((ROOT / "runpod_vllm_cpu_006.json").read_text())
    key = os.environ.get("VLLM_API_KEY", "")
    if not key:
        for line in (ROOT / ".env.local").read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "VLLM_API_KEY":
                key = value.strip().strip("\"").strip("'")
    if not key:
        raise SystemExit("VLLM_API_KEY is missing from the environment and .env.local")
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()

    def request(path, authenticated=False, body=None):
        headers = {"User-Agent": "APEX-Pod-Health/1.0"}
        if authenticated:
            headers["Authorization"] = f"Bearer {key}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(config["base_url"] + path,
                                     headers=headers,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=30, context=context) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, b""

    health, _ = request("/health")
    unauthorized, _ = request("/v1/models")
    models_status, models_body = request("/v1/models", True)
    print(json.dumps({"health_http": health, "unauthenticated_models_http": unauthorized,
                      "authenticated_models_http": models_status}))
    if health != 200 or unauthorized != 401 or models_status != 200:
        raise SystemExit("Service health or API authentication check failed")
    models = [m["id"] for m in json.loads(models_body).get("data", [])]
    if config["model"] not in models:
        raise SystemExit("Configured model is not served")
    started = time.monotonic()
    status, body = request("/v1/completions", True,
                           {"model": config["model"], "prompt": "The capital of France is",
                            "max_tokens": 8, "temperature": 0})
    result = json.loads(body) if status == 200 else {}
    passed = status == 200 and bool(result.get("choices"))
    print(json.dumps({"inference_http": status, "inference_verified": passed,
                      "model": config["model"], "latency_seconds": round(time.monotonic() - started, 3),
                      "usage": result.get("usage")}))
    if not passed:
        raise SystemExit("Inference request failed")


if __name__ == "__main__":
    main()
