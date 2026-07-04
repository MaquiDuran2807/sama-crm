"""Modelos de dominio para la app auth.

Contiene los modelos relacionados con la autenticación y gestión de usuarios
del portal SAMA.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Usuario extendido de SAMA que incluye contexto de tenant."""

    class UserType(models.TextChoices):
        ADMIN = "admin", "Administrador SAMA"
        TENANT_ADMIN = "tenant_admin", "Administrador de Tenant"
        AGENT = "agent", "Agente de Ventas"
        VIEWER = "viewer", "Solo Lectura"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="auth_users",
    )
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.AGENT,
    )
    phone_number = models.CharField(max_length=32, blank=True)
    avatar_url = models.URLField(blank=True)
    is_active_portal = models.BooleanField(default=True)
    last_login_portal = models.DateTimeField(null=True, blank=True)

    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to.",
        related_name="local_auth_user_set",
        related_query_name="local_auth_user",
        db_table="auth_user_groups",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="local_auth_user_permissions",
        related_query_name="local_auth_user_permissions",
        db_table="auth_user_user_permissions",
    )

    class Meta:
        ordering = ["username"]
        db_table = "auth_user"

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class LoginAttempt(models.Model):
    """Registro de intentos de inicio de sesión."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Exitoso"
        FAILED = "failed", "Fallido"
        LOCKED = "locked", "Bloqueado"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="login_attempts",
    )
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} - {self.status} - {self.created_at}"


class PasswordResetToken(models.Model):
    """Token para recuperación de contraseña."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self) -> bool:
        """Verifica si el token es válido."""
        return not self.used and self.expires_at > timezone.now()

    def __str__(self):
        return f"Token para {self.user.username}"