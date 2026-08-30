# -*- coding: utf-8 -*-
"""Scene Builder engine unit tests (Phase 2E, Task 24 / §20.1.6).

The engine is deterministic and provider-free, so these tests need no fake AI
provider: they verify scene mapping (order, narration, visual direction, pacing,
transitions, metadata) and G-5 identity preservation (characters referenced by
stable library ``character_id``).
"""

from apps.scene.engine import (
    assign_characters,
    build_scene_package,
    scene_kind,
)


class StubScript:
    def __init__(self, scenes, narration=""):
        self.scenes = scenes
        self.narration = narration


CHARACTERS = [
    {"id": "char_volcanologist", "name": "Volcanologist Maya"},
    {"id": "char_narrator", "name": "Narrator Team"},
]


class TestBuildScenePackage:
    def test_maps_script_scenes_into_ordered_package(self):
        scenes = [
            {
                "id": "s1",
                "heading": "Hook",
                "narration": "What causes a volcano to erupt?",
                "visual_notes": "Volcano wide shot.",
            },
            {
                "id": "s2",
                "heading": "Core concepts",
                "narration": "Magma rises.",
                "visual_notes": "Diagram of magma chamber.",
            },
        ]
        result = build_scene_package(StubScript(scenes), CHARACTERS)
        assert result["scene_count"] == 2
        first, second = result["scenes"]
        assert first["id"] == "s1" and first["order"] == 1
        assert second["id"] == "s2" and second["order"] == 2
        assert first["heading"] == "Hook"
        assert first["narration"] == "What causes a volcano to erupt?"
        assert first["visual_direction"] == "Volcano wide shot."
        assert first["pacing"] == "normal"
        assert first["transition"] == "cut"
        assert first["duration_seconds"] == 8
        assert first["metadata"]["kind"] == "intro"
        assert second["metadata"]["kind"] == "outro"

    def test_g5_references_characters_by_stable_id(self):
        scenes = [
            {
                "id": "s1",
                "heading": "Volcanologist Maya explains the eruption",
                "narration": "Maya walks through the field site.",
                "visual_notes": "Field jacket, notebook.",
            }
        ]
        result = build_scene_package(StubScript(scenes), CHARACTERS)
        assert result["scenes"][0]["characters"] == ["char_volcanologist"]

    def test_narration_falls_back_to_top_level(self):
        result = build_scene_package(StubScript([{"id": "s1", "heading": "H"}], narration="Global narration"), CHARACTERS)
        assert result["scenes"][0]["narration"] == "Global narration"

    def test_missing_visual_notes_yields_empty_direction(self):
        result = build_scene_package(
            StubScript([{"id": "s1", "heading": "H"}], narration="n"), CHARACTERS
        )
        assert result["scenes"][0]["visual_direction"] == ""

    def test_generates_stable_id_when_script_scene_has_none(self):
        result = build_scene_package(StubScript([{"heading": "H", "narration": "n"}]), CHARACTERS)
        assert result["scenes"][0]["id"].startswith("scene_")

    def test_empty_script_scenes_yield_empty_package(self):
        result = build_scene_package(StubScript([], narration="n"), CHARACTERS)
        assert result["scene_count"] == 0
        assert result["scenes"] == []


class TestAssignCharacters:
    def test_matches_character_by_name_in_scene_text(self):
        assert assign_characters("The Narrator Team leads the intro.", CHARACTERS) == [
            "char_narrator"
        ]

    def test_falls_back_to_first_when_no_match(self):
        assert assign_characters("Just a b-roll of the volcano.", CHARACTERS) == [
            "char_volcanologist"
        ]

    def test_empty_characters_yields_none(self):
        assert assign_characters("anything", []) == []


class TestSceneKind:
    def test_single_scene_is_body(self):
        assert scene_kind(1, 1) == "body"

    def test_first_is_intro_last_is_outro(self):
        assert scene_kind(1, 3) == "intro"
        assert scene_kind(3, 3) == "outro"
        assert scene_kind(2, 3) == "body"
