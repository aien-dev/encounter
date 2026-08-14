#!/usr/bin/env python3
"""Sibling Encounter membrane. Do not import hive membrane.admit."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tools.paths import get_root

ALLOW = "ALLOW"
DROP = "DROP"

# Copied strings from operator-hive/tools/membrane.py _SECRET_PATTERNS (2026-08-14).
# Keep in sync by test against hive source text, not by import.
SECRET_PATTERN_STRINGS = (
    r"\b(api[_-]?key|secret[_-]?key|private[_-]?key|access[_-]?token)\b\s*[:=]",
    r"\b(password|passwd|pwd)\s*[:=]\s*\S+",
    r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*",
    r"\bsk-[A-Za-z0-9]{16,}",
    r"\bxai-[A-Za-z0-9]{16,}",
    r"\bghp_[A-Za-z0-9]{20,}",
    r"\bAKIA[0-9A-Z]{12,}",
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"\b(aws_secret_access_key|openai_api_key)\b",
)
SECRET_PATTERNS = [re.compile(p, re.I) for p in SECRET_PATTERN_STRINGS]

HIVE_PATH_HINTS = (
    "/opt/atlas/operator-hive",
    "/opt/atlas/grok-hive",
    "/opt/atlas/secrets",
    "LESSONS.jsonl",
    "atlas-dials.json",
)


class MembraneDenied(RuntimeError):
    def __init__(self, reason: str, packet: dict[str, Any] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.packet = packet or {}


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_membrane() -> dict[str, Any]:
    path = get_root() / "MEMBRANE.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    roots = list(cfg.get("allowed_roots") or [])
    roots.append(str(get_root()))
    cfg["allowed_roots"] = sorted(set(roots))
    return cfg


def _log(event: dict[str, Any]) -> None:
    log_path = get_root() / "MEMBRANE_EVENTS.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def _norm_url(url: str) -> tuple[str, str, str, int]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port is None:
        port = 80 if parsed.scheme == "http" else 443
    base = f"{parsed.scheme}://{host}:{port}"
    return parsed.scheme, host, base, port


def check_path(path: str, cfg: dict[str, Any]) -> str:
    try:
        resolved = Path(path).resolve()
    except OSError:
        return DROP
    text = str(resolved)
    for forbid in cfg.get("forbid_roots") or []:
        if text == forbid or text.startswith(str(forbid).rstrip("/") + "/"):
            return DROP
    for allow in cfg.get("allowed_roots") or []:
        if text == allow or text.startswith(str(allow).rstrip("/") + "/"):
            return ALLOW
    return DROP


def check_topic(topic: str, cfg: dict[str, Any]) -> str:
    if topic in (cfg.get("hive_topics_deny") or []):
        return DROP
    if topic in (cfg.get("topic_receptors") or []):
        return ALLOW
    return DROP


def check_url(url: str, cfg: dict[str, Any]) -> str:
    try:
        scheme, host, base, _port = _norm_url(url)
    except Exception:
        return DROP
    if scheme != "http" or host != "127.0.0.1":
        return DROP
    for deny in cfg.get("http_deny_always") or []:
        if base == deny.rstrip("/") or url.startswith(deny.rstrip("/") + "/"):
            return DROP
    for allow in cfg.get("http_allow_default") or []:
        allow_n = allow.rstrip("/")
        if base == allow_n or url.startswith(allow_n + "/"):
            return ALLOW
    return DROP


def check_payload(payload: str) -> str:
    if not payload:
        return ALLOW
    for pat in SECRET_PATTERNS:
        if pat.search(payload):
            return DROP
    return ALLOW


def payload_has_hive_path(payload: str) -> bool:
    return any(hint in payload for hint in HIVE_PATH_HINTS)


def admit(packet: dict[str, Any]) -> str:
    """ALLOW or DROP. No ESCALATE."""
    cfg = load_membrane()
    reasons: list[str] = []
    decision = ALLOW
    if packet.get("path"):
        if check_path(str(packet["path"]), cfg) == DROP:
            decision = DROP
            reasons.append("path")
    if packet.get("url"):
        if check_url(str(packet["url"]), cfg) == DROP:
            decision = DROP
            reasons.append("url")
    if packet.get("topic") is not None and packet.get("topic") != "":
        if check_topic(str(packet["topic"]), cfg) == DROP:
            decision = DROP
            reasons.append("topic")
    if packet.get("payload") is not None:
        if check_payload(str(packet["payload"])) == DROP:
            decision = DROP
            reasons.append("secret")
    event = {
        "schema": "atlas.encounter.membrane_event/v1",
        "utc": _utc(),
        "decision": decision,
        "reasons": reasons,
        "keys": sorted(packet.keys()),
    }
    try:
        _log(event)
    except OSError:
        pass
    return decision


def require_admit(packet: dict[str, Any]) -> None:
    if admit(packet) != ALLOW:
        raise MembraneDenied("membrane DROP", packet)
