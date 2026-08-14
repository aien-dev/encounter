#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.parse_mouth import parse_mouth, utterance_kind  # noqa: E402


class ParserTests(unittest.TestCase):
    handles = {"atlas", "ava", "soren"}

    def test_trailing_json(self) -> None:
        raw = (
            "Ava, the rule is silence.\n\n"
            '{"schema":"atlas.encounter.mouth/v1","text":"Ava, the rule is silence.",'
            '"addresses":["ava"],"decline":false,"artifacts":[]}'
        )
        p = parse_mouth(raw, self.handles)
        self.assertTrue(p["parse_ok"])
        self.assertEqual(p["addresses"], ["ava"])
        self.assertFalse(p["decline"])

    def test_bare_decline(self) -> None:
        p = parse_mouth("DECLINE", self.handles)
        self.assertFalse(p["parse_ok"])
        self.assertTrue(p["decline"])
        self.assertEqual(utterance_kind(speaker="inh_atlas", decline=True, parse_ok=False, artifacts=[]), "decline")

    def test_parse_miss_no_invented_artifacts(self) -> None:
        p = parse_mouth("I think we all agree this is nice.", self.handles)
        self.assertFalse(p["parse_ok"])
        self.assertEqual(p["artifacts"], [])
        self.assertFalse(p["decline"])

    def test_at_handle_union(self) -> None:
        raw = (
            "Hey @atlas\n"
            '{"schema":"atlas.encounter.mouth/v1","text":"Hey @atlas","addresses":[],'
            '"decline":false,"artifacts":[]}'
        )
        p = parse_mouth(raw, self.handles)
        self.assertEqual(p["addresses"], ["atlas"])

    def test_scene_request_kind_accepted(self) -> None:
        raw = (
            '{"schema":"atlas.encounter.mouth/v1","text":"again",'
            '"addresses":[],"decline":false,"artifacts":[{"kind":"scene_request","body":{"protocol_id":"exp_address_v0"}}]}'
        )
        p = parse_mouth(raw, self.handles)
        self.assertTrue(p["parse_ok"])
        self.assertEqual(p["artifacts"][0]["kind"], "scene_request")


if __name__ == "__main__":
    unittest.main()
