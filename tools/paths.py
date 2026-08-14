"""Encounter root. Tests call set_root() on a temp tree."""
from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(os.environ.get("ENCOUNTER_ROOT", "/opt/atlas/encounter")).resolve()


def get_root() -> Path:
    return _ROOT


def set_root(path: str | Path) -> Path:
    global _ROOT
    _ROOT = Path(path).resolve()
    os.environ["ENCOUNTER_ROOT"] = str(_ROOT)
    return _ROOT
