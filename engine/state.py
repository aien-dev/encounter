"""Operator-facing snapshot for the cockpit. No hive paths."""
from __future__ import annotations

from typing import Any

from engine.scene import SceneError, current_scene_id, load_scene, scene_dir
from tools.paths import get_root
from tools.stores import read_json, read_jsonl


def _public_scene(scene: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in scene.items() if k not in {"started_mono", "binding_records"}}
    # keep binding ids only
    return out


def snapshot() -> dict[str, Any]:
    root = get_root()
    inhabitants = read_json(root / "registry" / "inhabitants.json", {"inhabitants": []})
    cards = []
    for rec in inhabitants.get("inhabitants") or []:
        handle = rec.get("handle")
        card = read_json(root / "inhabitants" / handle / "CARD.json", rec)
        cards.append(card)
    inventory = read_json(root / "inventory" / "INVENTORY.json", {})
    bindings = read_json(root / "registry" / "bindings.json", {"bindings": []})
    sid = current_scene_id()
    scene = None
    transcript: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    score = None
    if sid:
        try:
            scene = _public_scene(load_scene(sid))
            d = scene_dir(sid)
            transcript = read_jsonl(d / "TRANSCRIPT.jsonl")
            events = read_jsonl(d / "EVENTS.jsonl")[-40:]
            notes = read_jsonl(d / "NOTES.jsonl")
            score = read_json(d / "SCORE.json", None)
        except SceneError:
            scene = None
    scenes = []
    scdir = root / "scenes"
    if scdir.exists():
        for p in sorted(scdir.iterdir(), reverse=True):
            if (p / "SCENE.json").exists():
                s = read_json(p / "SCENE.json", {})
                scenes.append(
                    {
                        "id": s.get("id") or p.name,
                        "status": s.get("status"),
                        "protocol_id": s.get("protocol_id"),
                        "started_utc": s.get("started_utc"),
                    }
                )
    enabled = (root / "ENABLED").read_text(encoding="utf-8") == "true\n" if (root / "ENABLED").exists() else False
    return {
        "schema": "atlas.encounter.cockpit_state/v1",
        "enabled": enabled,
        "inhabitants": cards,
        "inventory": inventory,
        "bindings": bindings.get("bindings") or [],
        "current_id": sid,
        "scene": scene,
        "transcript": transcript,
        "events": events,
        "notes": notes,
        "score": score,
        "scenes": scenes[:20],
    }
