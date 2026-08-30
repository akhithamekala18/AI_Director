# -*- coding: utf-8 -*-
"""Character detection engine unit tests (Phase 2D, Task 23 / §20.1.4).

Verifies output parsing/normalisation and that detection depends only on the
provider abstraction (a fake adapter is used — no real provider is required).
Also covers G-5 identity preservation: re-detection with ``existing_ids`` keeps
a stable id for characters that persist unchanged.
"""

from apps.character.engine import (
    detect_characters,
    parse_character_output,
)


class FakeProvider:
    """Deterministic AIProviderAdapter stand-in for the character engine."""

    def __init__(self, content):
        self.content = content

    def generate_structured(self, prompt, schema=None, config=None):
        return {"content": self.content, "usage": {}, "cost": 0.03}


def _raw_char(name="Maya"):
    return {
        "name": name,
        "age": "30s",
        "gender": "female",
        "appearance": {
            "face_shape": "oval",
            "hair_style": "wavy",
            "hair_color": "brown",
            "eyes": "hazel",
            "skin_tone": "light",
        },
        "clothing": {"outfit": "field jacket", "colors": ["khaki", "green"], "style": "practical"},
        "accessories": ["helmet", "notebook"],
        "style": {"illustrative_style": "semi-realistic", "realism": "medium", "palette": ["earth"]},
    }


class TestParseCharacterOutput:
    def test_parses_dict_with_stable_ids(self):
        result = parse_character_output({"characters": [_raw_char()]})
        assert len(result) == 1
        char = result[0]
        assert char["name"] == "Maya"
        assert char["age"] == "30s"
        assert char["gender"] == "female"
        assert char["appearance"]["face_shape"] == "oval"
        assert char["clothing"]["outfit"] == "field jacket"
        assert "helmet" in char["accessories"]
        assert char["style"]["illustrative_style"] == "semi-realistic"
        assert char["id"].startswith("char_")

    def test_parses_json_string(self):
        import json

        result = parse_character_output(json.dumps({"characters": [_raw_char()]}))
        assert len(result) == 1
        assert result[0]["name"] == "Maya"

    def test_drops_unnamed_characters(self):
        result = parse_character_output(
            {"characters": [_raw_char(name="   "), _raw_char()]}
        )
        assert len(result) == 1

    def test_empty_input_degrades(self):
        assert parse_character_output("not json") == []
        assert parse_character_output({}) == []

    def test_g5_stable_id_preserved_across_regeneration(self):
        v1 = parse_character_output({"characters": [_raw_char()]})
        cid = v1[0]["id"]
        # Re-detection passes the existing (id, name) so the same character
        # keeps its id (G-5: identity preserved while attributes may change).
        v2 = parse_character_output(
            {"characters": [{**_raw_char(), "age": "40s"}]},
            existing_ids=[(cid, "Maya")],
        )
        assert v2[0]["id"] == cid
        assert v2[0]["age"] == "40s"


class TestDetectCharacters:
    def test_uses_provider_abstraction(self):
        class StubScript:
            script = "Volcanoes erupt when magma rises."
            narration = "Welcome."
            scenes = [{"id": "s1", "visual_notes": "volcano wide shot"}]

        provider = FakeProvider({"characters": [_raw_char()]})
        result = detect_characters(StubScript(), provider=provider)
        assert result["cost"] == 0.03
        assert len(result["characters"]) == 1
        assert result["characters"][0]["name"] == "Maya"
