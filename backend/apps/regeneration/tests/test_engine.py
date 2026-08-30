# -*- coding: utf-8 -*-
"""Regeneration engine tests: scope resolution, target validation, blast radius."""
import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.regeneration import engine
from apps.scene.models import SceneBuilder

from .helpers import approved_scene_builder, make_project


@pytest.mark.django_db
class TestResolveScope:
    def test_scene_scope(self):
        scope, sid = engine.resolve_scope("s1", False)
        assert scope == "scene"
        assert sid == "s1"

    def test_full_scope(self):
        scope, sid = engine.resolve_scope("anything", True)
        assert scope == "full"
        assert sid is None

    def test_missing_scene_id_raises(self):
        with pytest.raises(DjangoValidationError, match="scene_id is required"):
            engine.resolve_scope("", False)

    def test_none_scene_id_raises(self):
        with pytest.raises(DjangoValidationError, match="scene_id is required"):
            engine.resolve_scope(None, False)


@pytest.mark.django_db
class TestValidateSceneExists:
    def test_valid_scene(self, make_user):
        user = make_user(username="eng_valid")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        scene = engine.validate_scene_exists(builder, "s1")
        assert scene["id"] == "s1"

    def test_invalid_scene_id(self, make_user):
        user = make_user(username="eng_invalid")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        with pytest.raises(DjangoValidationError, match="does not exist"):
            engine.validate_scene_exists(builder, "nonexistent")

    def test_empty_scenes_raises(self, make_user):
        user = make_user(username="eng_empty")
        project = make_project(user)
        builder = SceneBuilder.objects.create(project=project, team=project.team, scenes=[])
        with pytest.raises(DjangoValidationError, match="no scenes"):
            engine.validate_scene_exists(builder, "s1")


@pytest.mark.django_db
class TestResolveTargets:
    def test_single_scene_targets(self, make_user):
        user = make_user(username="tgt_single")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.resolve_targets(builder, "s1", False, ["voice"])
        assert len(result["scopes"]) == 1
        assert result["scopes"][0]["id"] == "s1"
        assert result["media_types"] == ["voice"]
        assert result["scope"] == "scene"

    def test_full_targets_all_scenes(self, make_user):
        user = make_user(username="tgt_full")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.resolve_targets(builder, None, True, [])
        assert len(result["scopes"]) == 2

    def test_empty_media_types_gives_all(self, make_user):
        user = make_user(username="tgt_all")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.resolve_targets(builder, "s1", False, None)
        assert len(result["media_types"]) == 4

    def test_invalid_scene_raises(self, make_user):
        user = make_user(username="tgt_bad")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        with pytest.raises(DjangoValidationError, match="does not exist"):
            engine.resolve_targets(builder, "nonexistent", False, [])


@pytest.mark.django_db
class TestBuildRegenerationPayloads:
    def test_payloads_for_single_scene(self, make_user):
        user = make_user(username="pay_single")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.resolve_targets(builder, "s1", False, ["voice"])
        payloads = engine.build_regeneration_payloads(builder, result["scopes"], result["media_types"])
        assert len(payloads) == 1
        assert payloads[0]["scene_id"] == "s1"
        assert payloads[0]["media_type"] == "voice"

    def test_payloads_for_full_scenes(self, make_user):
        user = make_user(username="pay_full")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.resolve_targets(builder, None, True, ["voice", "music"])
        payloads = engine.build_regeneration_payloads(builder, result["scopes"], result["media_types"])
        assert len(payloads) == 4
        scene_ids = {p["scene_id"] for p in payloads}
        assert scene_ids == {"s1", "s2"}

    def test_blast_radius_only_target_scene(self, make_user):
        user = make_user(username="pay_blast")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.resolve_targets(builder, "s2", False, [])
        payloads = engine.build_regeneration_payloads(builder, result["scopes"], result["media_types"])
        for p in payloads:
            assert p["scene_id"] == "s2"
