# -*- coding: utf-8 -*-
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.accounts.serializers import LoginSerializer, RegisterSerializer, UserSerializer
from apps.audit.services import record_audit
from apps.core.enums import AuditAction
from apps.core.response import ok
from apps.notifications.services import notify_status


def _token_for(user):
    token, _ = Token.objects.get_or_create(user=user)
    return token.key


@method_decorator(csrf_exempt, name="dispatch")
class RegisterView(GenericAPIView):
    """Registration (Development Plan Day 4, §29.2).

    Creates the user with a hashed password (never plaintext), a personal
    workspace team and Creator membership, then issues a token and session.
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.create_user()
        login(request, user)
        record_audit(user, AuditAction.AUTH_REGISTER.value, target_type="user", target_id=user.id)
        notify_status(user, "Welcome to AI Director", "Your creator workspace is ready.")
        return ok(
            {"token": _token_for(user), "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(GenericAPIView):
    """Login (Development Plan Day 4, §29.2).

    Authenticates credentials; invalid credentials are rejected with 401.
    On success establishes a session and returns a token.
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request, username=serializer.validated_data["username"], password=serializer.validated_data["password"]
        )
        if user is None or not user.is_active:
            raise AuthenticationFailed("invalid credentials")
        login(request, user)
        record_audit(user, AuditAction.AUTH_LOGIN.value, target_type="user", target_id=user.id)
        return ok({"token": _token_for(user), "user": UserSerializer(user).data})


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        record_audit(request.user, AuditAction.AUTH_LOGOUT.value, target_type="user", target_id=request.user.id)
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return ok({"message": "logged out"})


class MeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        return ok({"user": self.get_serializer(request.user).data})
