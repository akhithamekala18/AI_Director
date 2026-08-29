# -*- coding: utf-8 -*-
"""Project service (Development Plan Day 6).

Encapsulates project creation, team-scoped queries, metadata updates, duplicate
and template flows, archive, and lifecycle transitions — all through the backend
state machine (invariant enforcement lives here, not in the UI).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.accounts.models import Team
from apps.audit.services import record_audit
from apps.core.enums import AuditAction, ProjectLifecycle
from apps.core.state_machine import validate_transition
from apps.projects.models import Project


def _team_of(user):
    """Return the user's primary team (their default membership)."""
    membership = user.memberships.select_related("team").order_by("id").first()
    if not membership:
        team = Team.objects.create(name=f"{user.username} workspace")
        membership = user.memberships.create(team=team, role="Creator")
    return membership.team


def create_project(user, topic, platform_target="", format_name="", is_template=False):
    if not topic or not topic.strip():
        raise django_validation("topic is required")
    with transaction.atomic():
        team = _team_of(user)
        project = Project.objects.create(
            team=team,
            owner=user,
            topic=topic.strip(),
            platform_target=platform_target,
            format=format_name,
            is_template=is_template,
        )
        record_audit(user, AuditAction.CREATE.value, "project", project.id, "created project")
    return project


def list_projects_for(user, include_archived=False):
    team_ids = user.memberships.values_list("team_id", flat=True)
    qs = Project.objects.filter(team_id__in=team_ids)
    if not include_archived:
        qs = qs.exclude(lifecycle_state=ProjectLifecycle.ARCHIVED.value)
    return qs.select_related("owner", "team")


def get_project(user, project_id):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return Project.objects.filter(id=project_id, team_id__in=team_ids).first()


def update_metadata(user, project, data):
    topic = data.get("topic")
    if topic is not None and not topic.strip():
        raise django_validation("topic cannot be empty")
    with transaction.atomic():
        # PATCH semantics: only fields supplied with a non-None value are
        # updated. Omitted fields preserve their existing values. This must
        # NOT write None into the non-nullable platform_target/format columns.
        update_fields = []
        if topic is not None:
            project.topic = topic.strip()
            update_fields.append("topic")
        if data.get("platform_target") is not None:
            project.platform_target = data["platform_target"]
            update_fields.append("platform_target")
        if data.get("format") is not None:
            project.format = data["format"]
            update_fields.append("format")
        update_fields.append("updated_at")
        project.save(update_fields=update_fields)
        record_audit(user, AuditAction.UPDATE.value, "project", project.id, "updated project metadata")
    return project


def transition(user, project, target_state):
    ok, error = validate_transition(ProjectLifecycle(project.lifecycle_state), ProjectLifecycle(target_state))
    if not ok:
        raise django_validation(error)
    with transaction.atomic():
        project.lifecycle_state = target_state
        project.save(update_fields=["lifecycle_state", "updated_at"])
        record_audit(
            user, AuditAction.LIFECYCLE_TRANSITION.value, "project", project.id, f"-> {target_state}"
        )
    return project


def archive_project(user, project):
    return transition(user, project, ProjectLifecycle.ARCHIVED.value)


def duplicate_project(user, project):
    with transaction.atomic():
        copy = Project.objects.create(
            team=project.team,
            owner=user,
            topic=project.topic,
            platform_target=project.platform_target,
            format=project.format,
            # A duplicate starts at Draft regardless of source state.
            lifecycle_state=ProjectLifecycle.DRAFT.value,
        )
        record_audit(user, AuditAction.DUPLICATE.value, "project", copy.id, f"duplicated from #{project.id}")
    return copy


def create_from_template(user, template):
    return duplicate_project(user, template)


def django_validation(message):
    return DjangoValidationError(message)


def next_required_action(lifecycle_state):
    """Derive the dashboard 'next required action' from the lifecycle state."""
    mapping = {
        ProjectLifecycle.DRAFT.value: "Start research",
        ProjectLifecycle.RESEARCHING.value: "Review and approve research",
        ProjectLifecycle.RESEARCH_APPROVED.value: "Generate script",
        ProjectLifecycle.SCRIPTING.value: "Review and approve script",
        ProjectLifecycle.SCRIPT_APPROVED.value: "Generate scenes",
        ProjectLifecycle.PRODUCING.value: "Review production",
        ProjectLifecycle.VIDEO_APPROVED.value: "Schedule video",
        ProjectLifecycle.SCHEDULED.value: "Preview and approve",
        ProjectLifecycle.PUBLISHED.value: "View analytics",
        ProjectLifecycle.ARCHIVED.value: "Archived",
    }
    return mapping.get(lifecycle_state, "Continue")
