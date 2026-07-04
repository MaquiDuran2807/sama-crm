from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status

from tenants.domain.models import Tenant, TenantUser


def validate_tenant_access(user, tenant_slug: str) -> Tenant:
    """Valida que *user* tenga acceso al tenant identificado por *tenant_slug*.

    Args:
        user: Usuario autenticado (o ``request.user``).
        tenant_slug: Slug público del tenant.

    Returns:
        La instancia de ``Tenant`` si el acceso está permitido.

    Raises:
        PermissionDenied: Si el usuario no tiene membresía en el tenant.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
    if user and getattr(user, "is_superuser", False):
        return tenant
    if not TenantUser.objects.filter(user=user, tenant=tenant).exists():
        raise PermissionDenied(
            f"No tienes acceso al tenant '{tenant.name}'. Contacta al administrador de SAMA."
        )
    return tenant


def require_tenant_access():
    """Decorador que valida acceso al tenant antes de ejecutar la vista.

    Extrae ``tenant_slug`` de los kwargs de la URL (parametro nombrado)
    o de ``request.query_params`` como fallback.

    Returns:
        Decorador de vista DRF que retorna 403 si el acceso es denegado.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                slug = kwargs.get("tenant_slug", "") or request.query_params.get("tenant_slug", "")
                if not slug:
                    raise PermissionDenied("El parámetro tenant_slug es obligatorio.")
                validate_tenant_access(request.user, slug)
            except PermissionDenied as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class TenantAccessMixin:
    """
    Mixin que valida que el usuario autenticado pertenezca al tenant solicitado.
    Los superusuarios tienen acceso libre a todos los tenants.
    """

    def get_tenant_from_request(self):
        tenant_slug = self.request.query_params.get("tenant_slug")
        if not tenant_slug:
            raise PermissionDenied("El parámetro tenant_slug es obligatorio para acceder a este recurso.")

        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

        # Superuser siempre tiene acceso (soporte de SAMA)
        if self.request.user and getattr(self.request.user, "is_superuser", False):
            return tenant

        # Verificar membresía del usuario normal
        if not TenantUser.objects.filter(user=self.request.user, tenant=tenant).exists():
            raise PermissionDenied(
                f"No tienes acceso al tenant '{tenant.name}'. Contacta al administrador de SAMA."
            )

        return tenant
