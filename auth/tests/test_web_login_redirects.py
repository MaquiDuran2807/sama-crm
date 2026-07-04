"""Pruebas del flujo web de autenticación.

Verifican que el login redirige según el rol del usuario y que el logout vuelve
al home público.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from tenants.domain.models import Tenant


User = get_user_model()


class AuthWebRedirectTests(TestCase):
    """Cubre login, selector de tenant y logout del portal."""

    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(name="Codensolar", slug="codensolar", is_active=True)
        self.tenant_user = User.objects.create_user(
            username="tenant.user",
            email="tenant@example.com",
            password="SmokePass123!",
            tenant=self.tenant,
        )
        self.superuser = User.objects.create_superuser(
            username="super.admin",
            email="admin@example.com",
            password="SmokePass123!",
        )

    def test_tenant_user_redirects_to_own_dashboard(self) -> None:
        """Un usuario tenant entra directo a su dashboard."""

        response = self.client.post(
            reverse("login"),
            {"username": self.tenant_user.username, "password": "SmokePass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("crm_web:dashboard", kwargs={"tenant_slug": self.tenant.slug}))

    def test_superuser_redirects_to_tenant_selector(self) -> None:
        """Un superuser aterriza en el selector de tenants."""

        response = self.client.post(
            reverse("login"),
            {"username": self.superuser.username, "password": "SmokePass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("auth-tenant-select"))

    def test_superuser_sees_active_tenants_in_selector(self) -> None:
        """La pantalla de selección muestra los tenants activos."""

        self.client.login(username=self.superuser.username, password="SmokePass123!")

        response = self.client.get(reverse("auth-tenant-select"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tenant.name)
        self.assertContains(response, reverse("crm_web:dashboard", kwargs={"tenant_slug": self.tenant.slug}))

    def test_logout_redirects_to_home(self) -> None:
        """Cerrar sesión devuelve al home público."""

        self.client.login(username=self.tenant_user.username, password="SmokePass123!")

        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))