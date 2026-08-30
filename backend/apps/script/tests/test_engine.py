# -*- coding: utf-8 -*-
"""Script engine unit tests (R5, Development Plan Day 22 / Overview §20.1.3).

Verifies output parsing and that gathering depends only on the provider
abstraction (a fake adapter is used — no real provider is required).
"""

from apps.script import engine
from apps.script.engine import parse_script_output

from .helpers import approved_research, make_project


class FakeProvider:
    """Deterministic AIProviderAdapter stand-in for the script engine."""

    def __init__(self, content):
        self.content = content

    def generate_structured(self, prompt, schema=None, config=None):
        return {"content": self.content, "usage": {}, "cost": 0.03}


class TestParseScriptOutput:
    def test_parses_dict(self):
        result = parse_script_output(
            {
                "title": "T",
                "outline": "O",
                "script": "S",
                "narration": "N",
                "scenes": [
                    {"id": "s1", "heading": "H", "narration": "n", "visual_notes": "v"}
                ],
                "captions": ["c1"],
                "hashtags": ["#x"],
            }
        )
        assert result["title"] == "T"
        assert result["outline"] == "O"
        assert result["script"] == "S"
        assert result["narration"] == "N"
        assert result["scenes"][0]["id"] == "s1"
        assert result["captions"] == ["c1"]
        assert result["hashtags"] == ["#x"]

    def test_parses_json_string(self):
        import json

        raw = json.dumps(
            {
                "title": "T2",
                "script": "S2",
                "narration": "N2",
                "scenes": [],
                "captions": [],
                "hashtags": [],
            }
        )
        result = parse_script_output(raw)
        assert result["title"] == "T2"
        assert result["script"] == "S2"

    def test_drops_malformed_scenes(self):
        result = parse_script_output(
            {
                "title": "T",
                "script": "S",
                "narration": "N",
                "scenes": ["not-a-dict", {"id": "s1"}],
                "captions": ["c1"],
                "hashtags": [],
            }
        )
        assert len(result["scenes"]) == 1
        assert result["scenes"][0]["id"] == "s1"

    def test_empty_input_degrades(self):
        result = parse_script_output("not json at all")
        assert result["title"] == ""
        assert result["script"] == ""
        assert result["scenes"] == []
        assert result["captions"] == []
        assert result["hashtags"] == []


class TestGatherScript:
    def test_uses_provider_abstraction(self, make_user):
        user = make_user(username="engine_script")
        project = make_project(user)
        research = approved_research(user, project)
        provider = FakeProvider(
            {
                "title": "T",
                "outline": "O",
                "script": "S",
                "narration": "N",
                "scenes": [{"id": "s1", "heading": "H"}],
                "captions": ["c1"],
                "hashtags": ["#x"],
            }
        )
        result = engine.gather_script(research, provider=provider)
        assert result["title"] == "T"
        assert result["script"] == "S"
        assert result["narration"] == "N"
        assert result["scenes"][0]["id"] == "s1"
        assert result["cost"] == 0.03
