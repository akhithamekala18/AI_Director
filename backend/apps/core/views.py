# -*- coding: utf-8 -*-
from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.core.response import ok
from apps.core.services import storage_access_token


class HealthzView(APIView):
    """Liveness probe (Development Plan Day 10, decision log DG-15).

    Public so infrastructure can reach it without authentication.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return JsonResponse({"status": "ok", "service": "ai-director-backend"})


class StorageTokenView(APIView):
    """Signed-delivery readiness endpoint (Overview §29.6, Development Plan Day 10).

    Authenticated users may request a short-lived read grant for an artifact key
    they own. This is the abstraction the B3 media pipeline will implement; the
    foundation proves the access-control boundary and rejects unauthorized reads.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        artifact_key = (request.data.get("artifact_key") or "").strip()
        if not artifact_key:
            raise ValidationError("artifact_key is required")
        token = storage_access_token(artifact_key)
        return ok({"grant": token})
