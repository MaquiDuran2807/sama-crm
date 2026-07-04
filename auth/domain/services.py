"""Servicios de dominio para la app auth.

Este módulo concentra la lógica de negocio pura relacionada con la autenticación,
verificación de permisos, gestión de sesiones y reglas de acceso.
"""

import secrets
from datetime import timedelta
from typing import Any

from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


def authenticate_user(
    username: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str = "",
) -> tuple[User | None, str]:
    """Autentica un usuario con username y contraseña.

    Args:
        username: Nombre de usuario.
        password: Contraseña sin validar.
        ip_address: Dirección IP del cliente.
        user_agent: User-Agent del cliente.

    Returns:
        Tupla (User | None, mensaje). Si es exitoso, User es la instancia.
    """
    from auth.domain.models import LoginAttempt

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        LoginAttempt.objects.create(
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            status=LoginAttempt.Status.FAILED,
        )
        return None, "Usuario o contraseña incorrectos"

    if not user.is_active:
        LoginAttempt.objects.create(
            user=user,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            status=LoginAttempt.Status.FAILED,
        )
        return None, "Usuario inactivo"

    if not user.check_password(password):
        LoginAttempt.objects.create(
            user=user,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            status=LoginAttempt.Status.FAILED,
        )
        return None, "Usuario o contraseña incorrectos"

    user.last_login_portal = timezone.now()
    user.save(update_fields=["last_login_portal"])

    LoginAttempt.objects.create(
        user=user,
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        status=LoginAttempt.Status.SUCCESS,
    )

    return user, "Autenticación exitosa"


def create_password_reset_token(user: User) -> str:
    """Genera un token de recuperación de contraseña.

    Args:
        user: Usuario que solicita el token.

    Returns:
        Token generado.
    """
    from auth.domain.models import PasswordResetToken

    token = secrets.token_urlsafe(32)
    expires = timezone.now() + timedelta(hours=24)

    PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=expires,
    )

    return token


def validate_password_reset_token(token: str) -> User | None:
    """Valida un token de recuperación de contraseña.

    Args:
        token: Token a validar.

    Returns:
        Usuario si el token es válido, None en caso contrario.
    """
    from auth.domain.models import PasswordResetToken

    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        return None

    if not reset_token.is_valid():
        return None

    return reset_token.user


def mark_token_as_used(token: str) -> bool:
    """Marca un token de recuperación como usado.

    Args:
        token: Token a marcar.

    Returns:
        True si se marcó correctamente, False si no existe.
    """
    from auth.domain.models import PasswordResetToken

    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        reset_token.used = True
        reset_token.save(update_fields=["used"])
        return True
    except PasswordResetToken.DoesNotExist:
        return False


def check_user_permission(user: Any, permission: str, tenant: Any = None) -> bool:
    """Verifica si un usuario tiene un permiso específico.

    Args:
        user: Usuario a verificar.
        permission: Permiso a comprobar (ej: 'crm.add_lead').
        tenant: Tenant contexto (opcional para permisos a nivel de tenant).

    Returns:
        True si tiene permiso, False en caso contrario.
    """
    if user.is_superuser:
        return True

    if user.user_type == user.UserType.ADMIN:
        return True

    if tenant and user.tenant != tenant:
        return False

    permission_map = {
        "crm.view_lead": [User.UserType.ADMIN, User.UserType.TENANT_ADMIN, User.UserType.AGENT, User.UserType.VIEWER],
        "crm.add_lead": [User.UserType.ADMIN, User.UserType.TENANT_ADMIN, User.UserType.AGENT],
        "crm.change_lead": [User.UserType.ADMIN, User.UserType.TENANT_ADMIN, User.UserType.AGENT],
        "crm.delete_lead": [User.UserType.ADMIN, User.UserType.TENANT_ADMIN],
        "tenants.view_tenant": [User.UserType.ADMIN, User.UserType.TENANT_ADMIN],
        "tenants.change_tenant": [User.UserType.ADMIN],
    }

    allowed_types = permission_map.get(permission, [])
    return user.user_type in allowed_types


def get_failed_login_attempts(username: str, minutes: int = 15) -> int:
    """Cuenta los intentos de login fallidos recientes.

    Args:
        username: Nombre de usuario.
        minutes: Ventana de tiempo en minutos.

    Returns:
        Cantidad de intentos fallidos.
    """
    from auth.domain.models import LoginAttempt

    threshold = timezone.now() - timedelta(minutes=minutes)
    return LoginAttempt.objects.filter(
        username=username,
        status=LoginAttempt.Status.FAILED,
        created_at__gte=threshold,
    ).count()


def is_account_locked(username: str, max_attempts: int = 5, minutes: int = 15) -> bool:
    """Verifica si una cuenta está bloqueada por excesos de intentos.

    Args:
        username: Nombre de usuario.
        max_attempts: Intentos máximos permitidos.
        minutes: Ventana de tiempo en minutos.

    Returns:
        True si está bloqueada, False en caso contrario.
    """
    return get_failed_login_attempts(username, minutes) >= max_attempts