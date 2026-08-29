# -*- coding: utf-8 -*-
from django.db.models import Q
from rest_framework.generics import GenericAPIView

from apps.accounts.permissions import HasCapability
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.core.response import ok


class AuditLogListView(GenericAPIView):
    """Audit-view surface: actor / time / reason (Development Plan Day 17, §5.8).

    Users see audit records they performed or that concern projects in the teams
    they belong to (team-scoped access, Overview §29.2).
    """

    serializer_class = AuditLogSerializer
    permission_classes = [HasCapability]
    capability = "view_audit"

    def get_queryset(self):
        from apps.projects.models import Project

        teams = self.request.user.memberships.values_list("team_id", flat=True)
        project_ids = Project.objects.filter(team_id__in=teams).values_list("id", flat=True)
        return AuditLog.objects.filter(
            Q(target_type="project", target_id__in=project_ids) | Q(actor_id=self.request.user.id)
        )

    def get(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())[:200]
        return ok({"audit_log": self.get_serializer(qs, many=True).data})
