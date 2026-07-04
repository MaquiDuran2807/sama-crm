"""Configuración del admin para la app auth."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from auth.domain.models import User, LoginAttempt, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin para el modelo User."""

    list_display = ["username", "email", "tenant", "user_type", "is_active", "is_active_portal"]
    list_filter = ["user_type", "is_active", "is_active_portal", "tenant"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["username"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Información SAMA", {"fields": ("tenant", "user_type", "phone_number", "avatar_url", "is_active_portal")}),
    )


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """Admin para LoginAttempt."""

    list_display = ["username", "status", "ip_address", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["username", "ip_address"]
    ordering = ["-created_at"]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin para PasswordResetToken."""

    list_display = ["user", "used", "expires_at", "created_at"]
    list_filter = ["used", "created_at"]
    search_fields = ["user__username", "token"]
    ordering = ["-created_at"]