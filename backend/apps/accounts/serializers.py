# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254, required=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        username = value.strip()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("username already taken")
        return username

    def validate_password(self, value):
        validate_password(value)
        return value

    def create_user(self):
        """Create the user, a personal workspace team, a Creator membership, and
        return the created user (caller wires notifications/audit)."""
        data = self.validated_data
        user = User.objects.create_user(
            username=data["username"],
            email=data.get("email", ""),
            password=data["password"],
        )
        from apps.accounts.models import Team

        team = Team.objects.create(name=f"{user.username} workspace")
        user.memberships.create(team=team, role="Creator")
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "mfa_enabled", "date_joined"]
        read_only_fields = fields

    def get_role(self, obj):
        return obj.get_primary_role()
