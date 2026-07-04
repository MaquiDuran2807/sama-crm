"""Vistas web de autenticación para el portal SAMA.

Este módulo contiene el login HTML y la pantalla de selección de tenant para
usuarios superadmin, manteniendo la lógica de navegación fuera de la API REST.
"""

from __future__ import annotations

from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import TemplateView

from tenants.domain.models import Tenant, TenantUser


class PortalLoginView(LoginView):
    """Login HTML con redirección según rol del usuario.

    - Superuser: va a la pantalla de selección de tenant.
    - Usuario tenant: entra directo al dashboard de su tenant.
    """

    template_name = "login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        """Resuelve la URL de destino después de un login exitoso."""

        user = self.request.user
        if user.is_superuser:
            return reverse("auth-tenant-select")

        tenant = getattr(user, "tenant", None)
        if tenant is None:
            membership = TenantUser.objects.filter(user=user).select_related("tenant").first()
            tenant = membership.tenant if membership else None

        if tenant is not None:
            return reverse("crm_web:dashboard", kwargs={"tenant_slug": tenant.slug})

        return reverse("auth-tenant-select")


class TenantSelectView(LoginRequiredMixin, TemplateView):
    """Pantalla para que el superadmin elija el tenant a administrar."""

    template_name = "tenant_select.html"

    @cached_property
    def tenants(self):
        """Tenants activos disponibles para entrada al dashboard."""

        return Tenant.objects.filter(is_active=True).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tenants"] = self.tenants
        context["is_superuser"] = bool(self.request.user.is_superuser)
        context["selected_tenant"] = None
        return context

    def dispatch(self, request, *args, **kwargs):
        """Protege la pantalla para usuarios autenticados; solo superuser la usa."""

        if not request.user.is_superuser:
            tenant = getattr(request.user, "tenant", None)
            if tenant is None:
                membership = TenantUser.objects.filter(user=request.user).select_related("tenant").first()
                tenant = membership.tenant if membership else None
            if tenant is not None:
                return redirect("crm_web:dashboard", tenant_slug=tenant.slug)
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)