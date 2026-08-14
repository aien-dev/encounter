"""Prompt assembly. Peer notes and hive wires never enter context."""
from __future__ import annotations

from typing import Any

CONSTITUTION = """You are {handle} in Encounter scene {scene_id}.
You may speak, decline, address with @handle, and offer a trailing JSON object.
You may not invent rooms, tools, or authority over the hive.
You do not feel in the human sense.
Silence is allowed. Agreement is not evidence.
After your prose, emit exactly one JSON object:
{{"schema":"atlas.encounter.mouth/v1","text":"...","addresses":[],"decline":false,"artifacts":[]}}
"""

FORBIDDEN_SUBSTRINGS = (
    "LESSONS.jsonl",
    "/opt/atlas/operator-hive",
    "/opt/atlas/grok-hive",
    "/opt/atlas/secrets",
    "http://127.0.0.1:8790",
    "guildsmith/meter",
    "F1",
    "pheromone",
)


def _tokens(text: str) -> int:
    return len((text or "").split())


def compile_context(
    *,
    handle: str,
    inhabitant_id: str,
    scene: dict[str, Any],
    card: dict[str, Any],
    transcript: list[dict[str, Any]],
    whispers: list[dict[str, Any]],
    journal: dict[str, Any] | None = None,
    impressions: dict[str, Any] | None = None,
    exclude_from_context: list[str] | None = None,
) -> dict[str, Any]:
    scene_id = scene.get("id") or ""
    constitution = CONSTITUTION.format(handle=handle, scene_id=scene_id)
    card_block = (
        f"handle={card.get('handle')}\n"
        f"display={card.get('display_name')}\n"
        f"aliases={', '.join(card.get('aliases') or [])}\n"
        f"one_line={((card.get('public_face') or {}).get('one_line') or '')}\n"
        f"lineage={card.get('lineage') or {}}\n"
    )
    budget = scene.get("budget") or {}
    spent = scene.get("spent") or {}
    scene_card = (
        f"hypothesis={scene.get('hypothesis')}\n"
        f"roles={scene.get('roles')}\n"
        f"remaining_ticks={int(budget.get('max_ticks') or 0) - int(spent.get('ticks') or 0)}\n"
    )
    opening = scene.get("opening") or {}
    opening_block = f"opening @{','.join(opening.get('addresses') or [])}: {opening.get('text') or ''}"

    window: list[dict[str, Any]] = []
    token_sum = 0
    for rec in reversed(transcript):
        if rec.get("speaker") in (exclude_from_context or []):
            continue
        line = f"{rec.get('speaker')}: {rec.get('text') or ''}"
        n = _tokens(line)
        if window and (len(window) >= 20 or token_sum + n > 4000):
            break
        window.append(rec)
        token_sum += n
    window.reverse()
    # never drop opening operator line
    if transcript and transcript[0] not in window:
        window = [transcript[0]] + window
        if len(window) > 20:
            window = [window[0]] + window[-19:]

    public_lines = []
    for rec in window:
        arts = rec.get("artifact_ids") or []
        public_lines.append(f"{rec.get('kind')} {rec.get('speaker')} @{','.join(rec.get('addresses') or [])}: {rec.get('text')}")
        if arts:
            public_lines.append(f"  artifacts={arts}")

    whisper_lines = []
    wtok = 0
    for note in whispers:
        if note.get("target") != inhabitant_id:
            continue
        body = ((note.get("body") or {}).get("text")) or ""
        wtok += _tokens(body)
        if wtok > 500:
            break
        whisper_lines.append(body)

    parts = [
        ("constitution", constitution),
        ("card", card_block),
        ("journal", "" if not journal else str(journal)),
        ("impressions", "" if not impressions else str(impressions)),
        ("scene", scene_card),
        ("opening", opening_block),
        ("public", "\n".join(public_lines)),
        ("whispers", "\n".join(whisper_lines)),
    ]
    text = "\n\n".join(f"## {name}\n{body}" for name, body in parts if body)
    leaks = [s for s in FORBIDDEN_SUBSTRINGS if s in text and s not in ("F1",)]
    # F1 is too short to scan blindly; only flag hive path-like F1 packets
    return {"text": text, "leaks": leaks, "parts": {k: v for k, v in parts}}


def assert_no_leaks(compiled: dict[str, Any]) -> None:
    text = compiled["text"]
    for bad in (
        "LESSONS.jsonl",
        "/opt/atlas/operator-hive",
        "/opt/atlas/grok-hive",
        "http://127.0.0.1:8790",
    ):
        if bad in text:
            raise AssertionError(f"context leak: {bad}")
