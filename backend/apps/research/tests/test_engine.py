# -*- coding: utf-8 -*-
"""Research engine unit tests (R5).

Verifies output parsing and that gathering depends only on the provider
abstraction (a fake adapter is used — no real provider is required).
"""

from apps.research import engine
from apps.research.engine import parse_research_output

from .helpers import make_project


class FakeProvider:
    """Deterministic AIProviderAdapter stand-in for the research engine."""

    def __init__(self, content):
        self.content = content

    def generate_structured(self, prompt, schema=None, config=None):
        return {"content": self.content, "usage": {}, "cost": 0.03}


class TestParseResearchOutput:
    def test_parses_dict(self):
        result = parse_research_output(
            {
                "summary": "S",
                "sources": [{"url": "https://a.example", "title": "T"}],
                "gaps": [{"type": "gap", "description": "D"}],
            }
        )
        assert result["summary"] == "S"
        assert result["sources"][0]["url"] == "https://a.example"
        assert result["gaps"][0]["gap_type"] == "gap"

    def test_parses_json_string(self):
        import json

        raw = json.dumps({"summary": "S2", "sources": [], "gaps": []})
        result = parse_research_output(raw)
        assert result["summary"] == "S2"

    def test_drops_malformed_sources(self):
        result = parse_research_output(
            {
                "summary": "S",
                "sources": [{"title": "no url"}, {"url": "https://ok.example"}],
                "gaps": [],
            }
        )
        assert len(result["sources"]) == 1
        assert result["sources"][0]["url"] == "https://ok.example"

    def test_rejects_non_gap_types(self):
        result = parse_research_output(
            {
                "summary": "S",
                "sources": [],
                "gaps": [{"type": "footnote", "description": "X"}],
            }
        )
        assert result["gaps"][0]["gap_type"] == "gap"

    def test_empty_input_degrades(self):
        result = parse_research_output("not json at all")
        assert result["summary"] == ""
        assert result["sources"] == []
        assert result["gaps"] == []


class TestGatherResearch:
    def test_uses_provider_abstraction(self, make_user):
        user = make_user(username="engine_user")
        project = make_project(user)
        provider = FakeProvider(
            {
                "summary": "S",
                "sources": [{"url": "https://a.example"}],
                "gaps": [{"type": "contradiction", "description": "D"}],
            }
        )
        result = engine.gather_research(project, provider=provider)
        assert result["summary"] == "S"
        assert result["sources"][0]["url"] == "https://a.example"
        assert result["gaps"][0]["gap_type"] == "contradiction"
        assert result["cost"] == 0.03
