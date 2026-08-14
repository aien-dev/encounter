"""Inference-only HTTP. Never :8790. No raw urllib outside this module and tests."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from tools.encounter_membrane import DROP, admit
from tools.paths import get_root  # noqa: F401


class HttpDenied(RuntimeError):
    pass


class HttpError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def encounter_http(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout_s: float = 180.0,
) -> tuple[int, bytes]:
    if admit({"url": url}) == DROP:
        raise HttpDenied(f"membrane DROP before connect: {url}")
    req_headers = {"User-Agent": "atlas-encounter/1"}
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        raise HttpError(f"HTTP {exc.code} {url}", status=exc.code, body=raw.decode("utf-8", "replace")) from exc
    except urllib.error.URLError as exc:
        raise HttpError(f"URL error {url}: {exc}") from exc


def get_json(url: str, *, timeout_s: float = 180.0) -> Any:
    _status, raw = encounter_http(url, method="GET", timeout_s=timeout_s)
    return json.loads(raw.decode("utf-8"))


def post_json(url: str, payload: dict[str, Any], *, timeout_s: float = 180.0) -> Any:
    body = json.dumps(payload).encode("utf-8")
    status, raw = encounter_http(
        url,
        method="POST",
        body=body,
        headers={"Content-Type": "application/json"},
        timeout_s=timeout_s,
    )
    if not raw:
        return {"_empty": True, "status": status}
    return json.loads(raw.decode("utf-8"))
