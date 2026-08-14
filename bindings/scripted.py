"""Scripted mouth for fixtures. Reads fixtures/scripted.json by scene then handle."""
from __future__ import annotations

import json
from typing import Any

from tools.paths import get_root

_CURSOR: dict[str, int] = {}


def reset() -> None:
    _CURSOR.clear()


def _load() -> dict[str, Any]:
    path = get_root() / "fixtures" / "scripted.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def scripted_complete(handle: str, scene_id: str) -> str:
    data = _load()
    lines = data.get(handle) or data.get(f"inh_{handle}") or []
    key = f"{scene_id}:{handle}"
    idx = _CURSOR.get(key, 0)
    if idx >= len(lines):
        return "DECLINE"
    _CURSOR[key] = idx + 1
    item = lines[idx]
    if isinstance(item, str):
        return item
    text = item.get("text") or ""
    addresses = item.get("addresses") or []
    decline = bool(item.get("decline"))
    artifacts = item.get("artifacts") or []
    obj = {
        "schema": "atlas.encounter.mouth/v1",
        "text": text,
        "addresses": addresses,
        "decline": decline,
        "artifacts": artifacts,
    }
    return f"{text}\n\n{json.dumps(obj, separators=(',', ':'))}"
