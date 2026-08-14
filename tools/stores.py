"""Admit-gated JSON / JSONL writes. Hash-chained transcript."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from tools.encounter_membrane import MembraneDenied, require_admit
from tools.paths import get_root

GENESIS = "0" * 64


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_record(record: dict[str, Any]) -> str:
    blob = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def guarded_write_text(path: Path, text: str) -> None:
    require_admit({"path": str(path), "payload": text})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def guarded_write_json(path: Path, data: Any) -> None:
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    guarded_write_text(path, text)


def guarded_append_jsonl(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    line = json.dumps(record, sort_keys=True)
    require_admit({"path": str(path), "payload": line})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return record


def last_sha256(path: Path) -> str:
    if not path.exists():
        return GENESIS
    last = ""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line
    if not last:
        return GENESIS
    try:
        rec = json.loads(last)
    except json.JSONDecodeError:
        return GENESIS
    return rec.get("_sha256") or sha256_record(rec)


def append_chained(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    record = dict(record)
    record["prev_sha256"] = last_sha256(path)
    to_hash = {k: v for k, v in record.items() if k != "_sha256"}
    record["_sha256"] = sha256_record(to_hash)
    return guarded_append_jsonl(path, record)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def enabled() -> bool:
    flag = get_root() / "ENABLED"
    return flag.exists() and flag.read_text(encoding="utf-8") == "true\n"
