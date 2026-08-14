"""Model-free trailing-JSON mouth parser. No LLM extractor."""
from __future__ import annotations

import json
import re
from typing import Any

SCHEMA = "atlas.encounter.mouth/v1"
HANDLE_RE = re.compile(r"(?:^|[\s])@([a-z][a-z0-9_]{0,31})\b")
MAX_OBJECT_BYTES = 4096
MAX_ARTIFACTS = 8
MAX_ARTIFACT_BODY = 2000

KNOWN_ARTIFACT_KINDS = {
    "claim",
    "procedure",
    "question",
    "disagreement",
    "playbook",
    "test_answer",
    "decline",
    "address",
    "scene_request",
}


def extract_handles(text: str, registry_handles: set[str]) -> list[str]:
    found: list[str] = []
    for match in HANDLE_RE.finditer(text or ""):
        handle = match.group(1)
        if handle in registry_handles or handle == "operator":
            if handle not in found:
                found.append(handle)
    return found


def _try_object(blob: str) -> dict[str, Any] | None:
    if len(blob.encode("utf-8")) > MAX_OBJECT_BYTES:
        return None
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and obj.get("schema") == SCHEMA:
        return obj
    return None


def _find_trailing_object(text: str) -> tuple[dict[str, Any] | None, str]:
    stripped = text.rstrip()
    if not stripped:
        return None, ""
    lines = stripped.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].lstrip().startswith("{ "):
            pass
        if lines[i].lstrip().startswith("{"):
            suffix = "\n".join(lines[i:])
            obj = _try_object(suffix)
            if obj is not None:
                prose = "\n".join(lines[:i]).rstrip()
                return obj, prose
    start = stripped.rfind("{")
    while start != -1:
        obj = _try_object(stripped[start:])
        if obj is not None:
            return obj, stripped[:start].rstrip()
        start = stripped.rfind("{", 0, start)
    return None, stripped


def _validate_artifacts(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw[:MAX_ARTIFACTS]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        if kind not in KNOWN_ARTIFACT_KINDS:
            continue
        body = item.get("body")
        if body is None:
            body = {}
        if isinstance(body, str):
            if len(body) > MAX_ARTIFACT_BODY:
                body = body[:MAX_ARTIFACT_BODY]
            body = {"text": body}
        elif isinstance(body, dict):
            text = body.get("text")
            if isinstance(text, str) and len(text) > MAX_ARTIFACT_BODY:
                body = {**body, "text": text[:MAX_ARTIFACT_BODY]}
        else:
            body = {"text": str(body)[:MAX_ARTIFACT_BODY]}
        out.append({"kind": kind, "body": body})
    return out


def parse_mouth(raw: str, registry_handles: set[str]) -> dict[str, Any]:
    obj, prose = _find_trailing_object(raw or "")
    if obj is None:
        token = (raw or "").strip()
        decline = token == "DECLINE"
        addresses = extract_handles(raw or "", registry_handles)
        return {
            "parse_ok": False,
            "text": token,
            "addresses": addresses,
            "decline": decline,
            "artifacts": [],
            "kind_hint": "decline" if decline else "unparsed",
        }
    text = str(obj.get("text") or "").strip() or prose
    addresses = list(obj.get("addresses") or [])
    addresses = [a for a in addresses if isinstance(a, str) and (a in registry_handles or a == "operator")]
    for handle in extract_handles((text or "") + "\n" + (prose or ""), registry_handles):
        if handle not in addresses:
            addresses.append(handle)
    decline = bool(obj.get("decline"))
    artifacts = _validate_artifacts(obj.get("artifacts"))
    return {
        "parse_ok": True,
        "text": text,
        "addresses": addresses,
        "decline": decline,
        "artifacts": artifacts,
        "kind_hint": "decline" if decline else "speech",
    }


def utterance_kind(
    *,
    speaker: str,
    decline: bool,
    parse_ok: bool,
    artifacts: list[dict[str, Any]],
    is_operator: bool = False,
    is_engine_card: bool = False,
) -> str:
    if is_operator:
        return "operator"
    if is_engine_card:
        return "engine_card"
    if decline:
        return "decline"
    if parse_ok and any(a.get("kind") == "question" for a in artifacts):
        return "question"
    if parse_ok:
        return "speech"
    return "unparsed"
