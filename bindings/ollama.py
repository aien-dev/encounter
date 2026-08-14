"""Ollama generate. think: false always in first slice."""
from __future__ import annotations

from typing import Any

from tools.encounter_http import post_json


def complete(binding: dict[str, Any], prompt: str) -> str:
    base = str(binding.get("base") or "http://127.0.0.1:11434").rstrip("/")
    url = base + "/api/generate"
    model = binding.get("model")
    if model != "qwen3:8b":
        raise RuntimeError("first slice may bind only qwen3:8b on :11434")
    timeout = float(binding.get("timeout_s") or 180)
    data = post_json(
        url,
        {
            "model": model,
            "prompt": "/no_think\n" + prompt,
            "stream": False,
            "think": False,
            "options": {"num_predict": 400},
        },
        timeout_s=timeout,
    )
    return str(data.get("response") or "")
