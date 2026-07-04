"""Tests para modelos de la app auth."""

import pytest
from django.utils import timezone
from auth.domain.models import User, LoginAttempt, PasswordResetToken


class TestUser:
    def test_create_admin_user(self, db):
        user = User.objects.create_user(
            username="admin",
            password="admin123",
            email="admin@sama.com",
            user_type=User.UserType.ADMIN,
        )
        assert user.username == "admin"
        assert user.user_type == "admin"
        assert user.is_active is True

    def test_create_agent_user(self, db):
        user = User.objects.create_user(
            username="agent",
            password="agent123",
            user_type=User.UserType.AGENT,
        )
        assert user.user_type == "agent"

    def test_default_user_type(self, db):
        user = User.objects.create_user(username="default_user", password="pass123")
        assert user.user_type == User.UserType.AGENT

    def test_str(self, db):
        user = User.objects.create_user(
            username="juan", password="pass123",
            user_type=User.UserType.TENANT_ADMIN,
        )
        assert "juan" in str(user)
        assert "Administrador de Tenant" in str(user)


class TestLoginAttempt:
    def test_create_failed_attempt(self, db):
        attempt = LoginAttempt.objects.create(
            username="testuser",
            ip_address="192.168.1.1",
            status=LoginAttempt.Status.FAILED,
        )
        assert attempt.status == "failed"
        assert str(attempt).startswith("testuser - failed")

    def test_create_success_attempt(self, db):
        user = User.objects.create_user(username="success", password="pass")
        attempt = LoginAttempt.objects.create(
            user=user,
            username="success",
            status=LoginAttempt.Status.SUCCESS,
        )
        assert attempt.status == "success"

    def test_ordering(self, db):
        from django.utils import timezone
        a1 = LoginAttempt.objects.create(
            username="u", status=LoginAttempt.Status.FAILED,
            created_at=timezone.now() - timezone.timedelta(seconds=1),
        )
        a2 = LoginAttempt.objects.create(username="u", status=LoginAttempt.Status.SUCCESS)
        qs = LoginAttempt.objects.all()
        assert list(qs) == [a2, a1]


class TestPasswordResetToken:
    def test_create_token(self, db):
        user = User.objects.create_user(username="reset_user", password="pass")
        token = PasswordResetToken.objects.create(
            user=user,
            token="test_token_123",
            expires_at=timezone.now() + timezone.timedelta(hours=24),
        )
        assert token.token == "test_token_123"
        assert token.used is False

    def test_is_valid_returns_true(self, db):
        user = User.objects.create_user(username="valid_user", password="pass")
        token = PasswordResetToken.objects.create(
            user=user,
            token="valid_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        assert token.is_valid() is True

    def test_is_valid_returns_false_when_expired(self, db):
        user = User.objects.create_user(username="expired_user", password="pass")
        token = PasswordResetToken.objects.create(
            user=user,
            token="expired_token",
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        assert token.is_valid() is False

    def test_is_valid_returns_false_when_used(self, db):
        user = User.objects.create_user(username="used_user", password="pass")
        token = PasswordResetToken.objects.create(
            user=user,
            token="used_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            used=True,
        )
        assert token.is_valid() is False

    def test_str(self, db):
        user = User.objects.create_user(username="str_user", password="pass")
        token = PasswordResetToken.objects.create(
            user=user, token="str_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        assert "str_user" in str(token)
