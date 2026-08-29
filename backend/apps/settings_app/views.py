# -*- coding: utf-8 -*-
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from apps.audit.services import record_audit
from apps.core.enums import AuditAction
from apps.core.response import ok
from apps.settings_app.models import StoredCredential, UserSettings
from apps.settings_app.serializers import StoredCredentialSerializer, UserSettingsSerializer
from apps.settings_app.services import encrypt_secret


class SettingsView(GenericAPIView):
    """Account/security settings foundation (Day 7). Creates on first read."""

    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return obj

    def get(self, request, *args, **kwargs):
        return ok({"settings": self.get_serializer(self.get_object()).data})

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_audit(request.user, AuditAction.SETTINGS_UPDATE.value, target_type="user", target_id=request.user.id)
        return ok({"settings": serializer.data})


class CredentialCreateView(GenericAPIView):
    """Store a platform credential encrypted at rest (Overview §29.4).

    The plaintext secret is encrypted before persistence and is never stored,
    serialized, or logged.
    """

    serializer_class = StoredCredentialSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        provider = (request.data.get("provider") or "").strip()
        label = (request.data.get("label") or "").strip()
        secret = request.data.get("secret")
        if not provider or not label or not secret:
            raise ValidationError("provider, label, and secret are required")
        encrypted = encrypt_secret(str(secret))
        credential = StoredCredential.objects.create(
            owner=request.user, provider=provider, label=label, encrypted_value=encrypted
        )
        record_audit(request.user, AuditAction.CREDENTIAL_SET.value, target_type="credential", target_id=credential.id)
        return ok({"credential": StoredCredentialSerializer(credential).data}, status=status.HTTP_201_CREATED)


class CredentialListView(GenericAPIView):
    serializer_class = StoredCredentialSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs = StoredCredential.objects.filter(owner=request.user, revoked=False)
        return ok({"credentials": self.get_serializer(qs, many=True).data})


class CredentialRevokeView(GenericAPIView):
    serializer_class = StoredCredentialSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        credential = StoredCredential.objects.filter(id=pk, owner=request.user).first()
        if not credential:
            raise NotFound("credential not found")
        credential.revoked = True
        credential.save(update_fields=["revoked"])
        record_audit(request.user, AuditAction.CREDENTIAL_REVOKED.value, target_type="credential", target_id=credential.id)
        return ok({"credential": StoredCredentialSerializer(credential).data})
