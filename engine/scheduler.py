"""Turn selection. Silence is legal. Opening inject is mandatory."""
from __future__ import annotations

from typing import Any

THRESHOLD = 1.0
SEAL = "SEAL"
SILENCE = "SILENCE"


def next_actor(scene: dict[str, Any], transcript: list[dict[str, Any]], last: dict[str, Any] | None) -> str:
    if scene.get("status") in {"sealed", "aborted", "frozen"}:
        return SEAL
    if scene.get("operator_forced_turn"):
        return str(scene["operator_forced_turn"])

    cast_meta: dict[str, dict[str, Any]] = scene.get("cast_meta") or {}
    last_addresses = list((last or {}).get("addresses") or [])
    last_kind = (last or {}).get("kind")
    last_speaker = (last or {}).get("speaker")
    spent = scene.setdefault("spent", {})
    budget = scene.get("budget") or {}
    roles = scene.get("roles") or {}
    protocol_critical = set(scene.get("protocol_critical") or [])
    nudge = scene.get("operator_nudge") or {}
    silenced = set(scene.get("silenced") or [])

    utterance_counts: dict[str, int] = {}
    last_spoke_ago: dict[str, int] = {}
    for rec in transcript:
        speaker = rec.get("speaker")
        if speaker:
            utterance_counts[speaker] = utterance_counts.get(speaker, 0) + 1
    for i, rec in enumerate(reversed(transcript)):
        speaker = rec.get("speaker")
        if speaker and speaker not in last_spoke_ago:
            last_spoke_ago[speaker] = i

    candidates: list[str] = []
    for inh_id in scene.get("cast") or []:
        meta = cast_meta.get(inh_id) or {}
        handle = meta.get("handle") or inh_id.replace("inh_", "", 1)
        if not meta.get("may_speak", True):
            continue
        if handle in silenced or inh_id in silenced:
            continue
        max_u = int(budget.get("max_utterances_per_inhabitant") or 6)
        if utterance_counts.get(inh_id, 0) >= max_u:
            continue
        binding_up = meta.get("binding_up", True)
        if not binding_up and not scene.get("allow_degraded_skip"):
            if inh_id in protocol_critical:
                return SEAL
            continue
        candidates.append(inh_id)

    if not candidates:
        idle = int(spent.get("idle_ticks") or 0)
        if idle < 2:
            return SILENCE
        return SEAL

    scores: dict[str, float] = {}
    declined = set(scene.get("declined_last_offer") or [])
    for inh_id in candidates:
        meta = cast_meta.get(inh_id) or {}
        handle = meta.get("handle") or inh_id.replace("inh_", "", 1)
        s = 0.0
        if last_addresses == [handle]:
            s += 5.0
        elif handle in last_addresses:
            s += 3.0
        if last_kind == "question" and handle in last_addresses:
            s += 1.0
        if inh_id == roles.get("witness") and last_addresses == []:
            s += 1.5
        s += 0.4 * float(last_spoke_ago.get(inh_id, len(transcript)))
        if last_speaker == inh_id:
            s -= 2.0
        klass = meta.get("class") or ""
        if klass in ("boston_tunnel", "slow_local") and handle not in last_addresses:
            s -= 1.0
        if inh_id in declined and last_speaker == last_speaker:
            s -= 100
        if inh_id in protocol_critical and last_addresses == []:
            s += 0.5
        s += float(nudge.get(inh_id, 0) or 0)
        scores[inh_id] = s

    winner = max(scores, key=lambda k: scores[k])
    if scores[winner] < THRESHOLD:
        spent["idle_ticks"] = int(spent.get("idle_ticks") or 0) + 1
        if spent["idle_ticks"] >= 2:
            return SEAL
        return SILENCE
    spent["idle_ticks"] = 0
    return winner
