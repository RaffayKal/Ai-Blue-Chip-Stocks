#!/usr/bin/env python3
"""Receive validated read-only Robinhood MCP quote payloads over HTTP."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ingest_robinhood_crypto_quote_snapshot import normalize
from project_root import ROOT

SNAPSHOT = ROOT / "data" / "robinhood_crypto_quote_snapshot.json"
HOST = os.getenv("ROBINHOOD_MCP_RELAY_HOST", "127.0.0.1")
PORT = int(os.getenv("ROBINHOOD_MCP_RELAY_PORT", "8765"))
TOKEN = os.getenv("ROBINHOOD_MCP_RELAY_TOKEN", "")
MAX_BODY_BYTES = 65536


def write_snapshot(payload):
    normalized = normalize(payload)
    normalized["relay_received_at"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(SNAPSHOT)
    return normalized


class RelayHandler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        supplied = self.headers.get("Authorization", "")
        return bool(TOKEN) and supplied == f"Bearer {TOKEN}"

    def do_GET(self):
        if self.path == "/v1/robinhood/crypto-quote":
            if not self.authorized():
                self.send_json(401, {"status": "unauthorized"})
                return
            try:
                snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self.send_json(404, {"status": "snapshot_unavailable"})
                return
            self.send_json(200, snapshot)
            return
        if self.path != "/health":
            self.send_json(404, {"status": "not_found"})
            return
        self.send_json(200, {
            "status": "ready" if TOKEN else "blocked_missing_relay_token",
            "execution_authority": False,
            "snapshot_path": str(SNAPSHOT),
        })

    def do_POST(self):
        if self.path != "/v1/robinhood/crypto-quote":
            self.send_json(404, {"status": "not_found"})
            return
        if not self.authorized():
            self.send_json(401, {"status": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("invalid body size")
            payload = json.loads(self.rfile.read(length))
            snapshot = write_snapshot(payload)
        except (ValueError, TypeError, json.JSONDecodeError, KeyError) as exc:
            self.send_json(400, {"status": "rejected", "reason": str(exc)})
            return
        self.send_json(200, {
            "status": "accepted",
            "provider": "Robinhood",
            "quote_timestamp": snapshot["quote_timestamp"],
            "execution_authority": False,
        })

    def log_message(self, format_string, *args):
        print(f"ROBINHOOD_MCP_RELAY: {format_string % args}", flush=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("BLOCKED: ROBINHOOD_MCP_RELAY_TOKEN is required")
    print(f"ROBINHOOD_MCP_RELAY: LISTENING {HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), RelayHandler).serve_forever()
