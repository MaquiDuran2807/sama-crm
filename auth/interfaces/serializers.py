"""Serializers para la app auth."""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from auth.domain.models import LoginAttempt, PasswordResetToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer para el modelo User."""

    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    user_type_display = serializers.CharField(source="get_user_type_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "tenant",
            "tenant_name",
            "user_type",
            "user_type_display",
            "phone_number",
            "avatar_url",
            "is_active",
            "is_active_portal",
            "last_login_portal",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined", "last_login_portal"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear usuarios."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
            "tenant",
            "user_type",
            "phone_number",
        ]

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Las contraseñas no coinciden"})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer para el login."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class LoginAttemptSerializer(serializers.ModelSerializer):
    """Serializer para LoginAttempt."""

    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = LoginAttempt
        fields = ["id", "user", "user_username", "username", "ip_address", "status", "created_at"]


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer para solicitar reseteo de contraseña."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer para confirmar reseteo de contraseña."""

    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Las contraseñas no coinciden"})
        return data