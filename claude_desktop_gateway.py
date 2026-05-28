from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


MIMO_PRO_MODEL = "mimo-v2.5-pro"
MIMO_GENERAL_MODEL = "mimo-v2.5"
MIMO_TTS_MODEL = "mimo-v2.5-tts"
MIMO_ASR_MODEL = "mimo-v2.5-asr"
DEFAULT_MODEL = MIMO_PRO_MODEL

DESKTOP_MODELS = [
    ("claude-opus-4-7", "MiMo-V2.5-Pro - 代码 / 主力"),
    ("claude-sonnet-4-5", "MiMo-V2.5 - 多模态 / 通用"),
    ("claude-haiku-4-5", "MiMo-V2.5 - 通用 / 轻量"),
]


def load_settings() -> dict:
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return {}
    with settings_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_model(model: str | None) -> str:
    if not model:
        return DEFAULT_MODEL
    aliases = {
        "claude-opus-4-7": MIMO_PRO_MODEL,
        "claude-opus-4.7": MIMO_PRO_MODEL,
        "claude-sonnet-4-5": MIMO_GENERAL_MODEL,
        "claude-haiku-4-5": MIMO_GENERAL_MODEL,
        "mimo-v2.5-pro": MIMO_PRO_MODEL,
        "mimo-v2.5": MIMO_GENERAL_MODEL,
        "mimo-v2.5-tts": MIMO_TTS_MODEL,
        "mimo-v2.5-asr": MIMO_ASR_MODEL,
    }
    lowered = model.strip().lower()
    return aliases.get(lowered, lowered)


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "ClaudeDesktopGateway/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("", "/"):
            self._json(200, {"ok": True, "service": "claude-desktop-gateway"})
            return
        if path == "/v1/models":
            self._json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "type": "model",
                            "id": model_id,
                            "display_name": display_name,
                            "created_at": "2025-01-01T00:00:00Z",
                        }
                        for model_id, display_name in DESKTOP_MODELS
                    ],
                },
            )
            return
        self._json(404, {"error": {"message": f"Unknown endpoint: {path}"}})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length) if length else b"{}"

        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": {"message": "Invalid JSON body"}})
            return

        if isinstance(payload, dict) and "model" in payload:
            payload["model"] = normalize_model(str(payload.get("model")))

        try:
            status, headers, body = self._forward(path, payload)
        except Exception as exc:
            self._json(502, {"error": {"message": f"Gateway upstream failed: {exc}"}})
            return

        self.send_response(status)
        content_type = headers.get("content-type", "application/json")
        self.send_header("content-type", content_type)
        self.send_header("cache-control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _forward(self, path: str, payload: dict) -> tuple[int, dict, bytes]:
        upstream = self.server.upstream_base_url.rstrip("/")  # type: ignore[attr-defined]
        api_key = self.server.upstream_api_key  # type: ignore[attr-defined]
        url = upstream + path
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "accept": "application/json",
            "x-api-key": api_key,
            "anthropic-version": self.headers.get("anthropic-version", "2023-06-01"),
        }
        if self.headers.get("anthropic-beta"):
            headers["anthropic-beta"] = self.headers["anthropic-beta"]
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=15721, type=int)
    args = parser.parse_args()

    settings = load_settings()
    upstream_base_url = (
        os.environ.get("CLAUDE_GATEWAY_UPSTREAM")
        or settings.get("base_url")
        or settings.get("apiEndpoint")
        or "https://token-plan-cn.xiaomimimo.com/anthropic"
    )
    upstream_api_key = os.environ.get("CLAUDE_GATEWAY_API_KEY") or settings.get("api_key")
    if not upstream_api_key:
        raise SystemExit("Missing upstream API key. Put api_key in ~/.claude/settings.json.")

    server = ThreadingHTTPServer((args.host, args.port), GatewayHandler)
    server.upstream_base_url = upstream_base_url  # type: ignore[attr-defined]
    server.upstream_api_key = upstream_api_key  # type: ignore[attr-defined]
    print(f"Claude Desktop gateway listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
