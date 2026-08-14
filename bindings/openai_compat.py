"""OpenAI-compat mouth. Uses encounter_http only."""
from __future__ import annotations

from typing import Any

from tools.encounter_http import post_json


def complete(binding: dict[str, Any], prompt: str) -> str:
    base = str(binding.get("base") or "").rstrip("/")
    url = base + "/chat/completions"
    model = binding.get("model")
    timeout = float(binding.get("timeout_s") or 180)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Follow the Encounter constitution. End with the trailing JSON object."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.4,
    }
    data = post_json(url, body, timeout_s=timeout)
    try:
        return str(data["choices"][0]["message"]["content"] or "")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"bad chat completion: {data!r}") from exc
