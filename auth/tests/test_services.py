"""Tests para servicios de dominio de auth."""

import pytest
from django.utils import timezone
from auth.domain.models import User, LoginAttempt, PasswordResetToken
from auth.domain.services import (
    authenticate_user,
    create_password_reset_token,
    validate_password_reset_token,
    mark_token_as_used,
    check_user_permission,
    get_failed_login_attempts,
    is_account_locked,
)


class TestAuthenticateUser:
    def test_successful_login(self, db):
        user = User.objects.create_user(
            username="testuser", password="correct_password",
            user_type=User.UserType.AGENT,
        )
        authenticated, msg = authenticate_user("testuser", "correct_password")
        assert authenticated == user
        assert "exitosa" in msg

    def test_failed_login_wrong_password(self, db):
        User.objects.create_user(username="testuser", password="correct")
        authenticated, msg = authenticate_user("testuser", "wrong")
        assert authenticated is None
        assert "incorrectos" in msg

    def test_failed_login_nonexistent_user(self, db):
        authenticated, msg = authenticate_user("noexiste", "pass")
        assert authenticated is None
        assert "incorrectos" in msg

    def test_inactive_user_cannot_login(self, db):
        User.objects.create_user(
            username="inactive", password="pass",
            is_active=False,
        )
        authenticated, msg = authenticate_user("inactive", "pass")
        assert authenticated is None
        assert "inactivo" in msg

    def test_creates_login_attempt_on_success(self, db):
        User.objects.create_user(username="logme", password="pass")
        authenticate_user("logme", "pass")
        assert LoginAttempt.objects.filter(username="logme", status="success").exists()

    def test_creates_login_attempt_on_failure(self, db):
        authenticate_user("failuser", "wrong")
        assert LoginAttempt.objects.filter(username="failuser", status="failed").exists()

    def test_records_ip_address(self, db):
        User.objects.create_user(username="ipuser", password="pass")
        authenticate_user("ipuser", "pass", ip_address="10.0.0.1")
        attempt = LoginAttempt.objects.filter(username="ipuser").first()
        assert attempt.ip_address == "10.0.0.1"


class TestCreatePasswordResetToken:
    def test_creates_token(self, db):
        user = User.objects.create_user(username="resetme", password="pass")
        token = create_password_reset_token(user)
        assert PasswordResetToken.objects.filter(token=token).exists()

    def test_token_is_string(self, db):
        user = User.objects.create_user(username="tokengen", password="pass")
        token = create_password_reset_token(user)
        assert isinstance(token, str)
        assert len(token) > 10

    def test_token_has_expiration(self, db):
        user = User.objects.create_user(username="checkexp", password="pass")
        token_str = create_password_reset_token(user)
        token = PasswordResetToken.objects.get(token=token_str)
        assert token.expires_at > timezone.now()


class TestValidatePasswordResetToken:
    def test_valid_token_returns_user(self, db):
        user = User.objects.create_user(username="validtoken", password="pass")
        token_str = create_password_reset_token(user)
        result = validate_password_reset_token(token_str)
        assert result == user

    def test_invalid_token_returns_none(self, db):
        result = validate_password_reset_token("nonexistent_token")
        assert result is None

    def test_expired_token_returns_none(self, db):
        user = User.objects.create_user(username="exp", password="pass")
        token = PasswordResetToken.objects.create(
            user=user,
            token="expired_token_val",
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        result = validate_password_reset_token("expired_token_val")
        assert result is None

    def test_used_token_returns_none(self, db):
        user = User.objects.create_user(username="usedtoken", password="pass")
        PasswordResetToken.objects.create(
            user=user, token="used",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            used=True,
        )
        result = validate_password_reset_token("used")
        assert result is None


class TestMarkTokenAsUsed:
    def test_marks_token(self, db):
        user = User.objects.create_user(username="markuser", password="pass")
        token_str = create_password_reset_token(user)
        result = mark_token_as_used(token_str)
        assert result is True
        token = PasswordResetToken.objects.get(token=token_str)
        assert token.used is True

    def test_nonexistent_token_returns_false(self, db):
        result = mark_token_as_used("no_exist")
        assert result is False


class TestCheckUserPermission:
    def test_superuser_has_all_permissions(self, db):
        user = User.objects.create_user(
            username="super", password="pass",
            is_superuser=True,
        )
        assert check_user_permission(user, "crm.add_lead") is True
        assert check_user_permission(user, "crm.delete_lead") is True

    def test_admin_has_all_permissions(self, db):
        user = User.objects.create_user(
            username="appadmin", password="pass",
            user_type=User.UserType.ADMIN,
        )
        assert check_user_permission(user, "crm.add_lead") is True
        assert check_user_permission(user, "crm.delete_lead") is True
        assert check_user_permission(user, "tenants.change_tenant") is True

    def test_agent_can_add_lead(self, db):
        user = User.objects.create_user(
            username="agent", password="pass",
            user_type=User.UserType.AGENT,
        )
        assert check_user_permission(user, "crm.add_lead") is True
        assert check_user_permission(user, "crm.view_lead") is True

    def test_agent_cannot_delete_lead(self, db):
        user = User.objects.create_user(
            username="agent2", password="pass",
            user_type=User.UserType.AGENT,
        )
        assert check_user_permission(user, "crm.delete_lead") is False

    def test_viewer_can_only_view(self, db):
        user = User.objects.create_user(
            username="viewer", password="pass",
            user_type=User.UserType.VIEWER,
        )
        assert check_user_permission(user, "crm.view_lead") is True
        assert check_user_permission(user, "crm.add_lead") is False
        assert check_user_permission(user, "crm.change_lead") is False

    def test_unknown_permission_returns_false(self, db):
        user = User.objects.create_user(
            username="any", password="pass",
            user_type=User.UserType.AGENT,
        )
        assert check_user_permission(user, "unknown.permission") is False

    def test_wrong_tenant_returns_false(self, db, tenant):
        user = User.objects.create_user(
            username="wrongtenant", password="pass",
            user_type=User.UserType.AGENT,
        )
        other_tenant = type(tenant).objects.create(
            name="Other", slug="other",
        )
        assert check_user_permission(user, "crm.view_lead", tenant=other_tenant) is False


class TestGetFailedLoginAttempts:
    def test_counts_recent_failures(self, db):
        for i in range(3):
            LoginAttempt.objects.create(
                username="target", status=LoginAttempt.Status.FAILED,
            )
        count = get_failed_login_attempts("target")
        assert count >= 3

    def test_ignores_old_attempts(self, db):
        LoginAttempt.objects.create(
            username="olduser", status=LoginAttempt.Status.FAILED,
            created_at=timezone.now() - timezone.timedelta(hours=1),
        )
        count = get_failed_login_attempts("olduser", minutes=30)
        assert count == 0


class TestIsAccountLocked:
    def test_locked_when_exceeded(self, db):
        for i in range(5):
            LoginAttempt.objects.create(
                username="lockeduser", status=LoginAttempt.Status.FAILED,
            )
        assert is_account_locked("lockeduser", max_attempts=5) is True

    def test_not_locked_below_threshold(self, db):
        LoginAttempt.objects.create(
            username="freeuser", status=LoginAttempt.Status.FAILED,
        )
        assert is_account_locked("freeuser", max_attempts=5) is False
