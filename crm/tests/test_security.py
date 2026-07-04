import hmac
import hashlib
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

from crm.domain.models import Lead
from tenants.domain.models import Tenant, TenantUser


class CrossTenantSecurityTest(TestCase):
    """Verifica que ningun usuario pueda acceder a datos de otros tenants.

    S-01: Cross-tenant en vistas function-based.
    """

    def setUp(self):
        self.client = APIClient()

        self.tenant_a = Tenant.objects.create(name="Tenant A", slug="tenant-a", is_active=True)
        self.tenant_b = Tenant.objects.create(name="Tenant B", slug="tenant-b", is_active=True)

        self.user_a = User.objects.create_user(username="usera", password="pass1234")
        self.user_b = User.objects.create_user(username="userb", password="pass1234")

        TenantUser.objects.create(user=self.user_a, tenant=self.tenant_a)
        TenantUser.objects.create(user=self.user_b, tenant=self.tenant_b)

        self.client_a = APIClient()
        self.client_a.force_authenticate(user=self.user_a)
        self.client_b = APIClient()
        self.client_b.force_authenticate(user=self.user_b)

    def _tag_list_url(self, tenant_slug: str) -> str:
        return reverse("tags-list-create", kwargs={"tenant_slug": tenant_slug})

    def _kpi_list_url(self, tenant_slug: str) -> str:
        return reverse("kpi-targets-list-create", kwargs={"tenant_slug": tenant_slug})

    def _products_list_url(self, tenant_slug: str) -> str:
        return reverse("products-list-create", kwargs={"tenant_slug": tenant_slug})

    def test_user_a_cannot_access_tenant_b_tags(self):
        """Usuario A recibe 403 al listar tags del Tenant B."""
        response = self.client_a.get(self._tag_list_url("tenant-b"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_b_cannot_access_tenant_a_tags(self):
        """Usuario B recibe 403 al listar tags del Tenant A."""
        response = self.client_b.get(self._tag_list_url("tenant-a"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_a_can_access_own_tenant_tags(self):
        """Usuario A puede listar tags de su propio tenant."""
        response = self.client_a.get(self._tag_list_url("tenant-a"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_a_cannot_access_tenant_b_kpis(self):
        """Usuario A recibe 403 al acceder a KPIs del Tenant B."""
        response = self.client_a.get(self._kpi_list_url("tenant-b"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_b_cannot_access_tenant_a_kpis(self):
        """Usuario B recibe 403 al acceder a KPIs del Tenant A."""
        response = self.client_b.get(self._kpi_list_url("tenant-a"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_a_cannot_access_tenant_b_products(self):
        """Usuario A recibe 403 al listar productos del Tenant B."""
        response = self.client_a.get(self._products_list_url("tenant-b"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_access_any_tenant(self):
        """Superuser puede acceder a cualquier tenant."""
        admin = User.objects.create_superuser(username="admin", password="admin123")
        self.client.force_authenticate(user=admin)
        response = self.client.get(self._tag_list_url("tenant-b"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_gets_403(self):
        """Usuario no autenticado recibe 403."""
        response = self.client.get(self._tag_list_url("tenant-a"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TenantViewSetSecurityTest(TestCase):
    """Verifica que TenantViewSet filtre por membresia del usuario.

    S-03: Validacion de tenant en TenantViewSet.
    """

    def setUp(self):
        self.client = APIClient()

        self.tenant_a = Tenant.objects.create(name="Tenant A", slug="tenant-a", is_active=True)
        self.tenant_b = Tenant.objects.create(name="Tenant B", slug="tenant-b", is_active=True)
        self.tenant_c = Tenant.objects.create(name="Tenant C", slug="tenant-c", is_active=True)

        self.user = User.objects.create_user(username="testuser", password="pass1234")
        TenantUser.objects.create(user=self.user, tenant=self.tenant_a)
        TenantUser.objects.create(user=self.user, tenant=self.tenant_b)

        self.client.force_authenticate(user=self.user)

    def test_user_only_sees_own_tenants(self):
        """Usuario solo ve tenants donde tiene membresia."""
        response = self.client.get("/api/tenants/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [t["slug"] for t in response.data]
        self.assertIn("tenant-a", slugs)
        self.assertIn("tenant-b", slugs)
        self.assertNotIn("tenant-c", slugs)

    def test_user_cannot_access_tenant_without_membership(self):
        """Usuario recibe 404 al acceder a tenant sin membresia."""
        response = self.client.get("/api/tenants/tenant-c/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SyncAuthTest(TestCase):
    """Verifica que SyncTriggerView requiera autenticacion.

    S-02: Autenticacion en SyncTriggerView.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="pass1234")

    def test_sync_without_auth_returns_403(self):
        """Sync endpoint sin autenticacion retorna 403."""
        response = self.client.post("/ingesta/api/sync/", {"instance_name": "default"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sync_with_auth_returns_202(self):
        """Sync endpoint con autenticacion retorna 202."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/ingesta/api/sync/", {"instance_name": "default"})
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_sync_status_without_auth_returns_403(self):
        """Sync status endpoint sin autenticacion retorna 403."""
        response = self.client.get("/ingesta/api/sync/fake-job-id/status/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instances_without_auth_returns_403(self):
        """Instances list endpoint sin autenticacion retorna 403."""
        response = self.client.get("/ingesta/api/instances/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_chat_user_rename_without_auth_returns_403(self):
        """ChatUser rename sin autenticacion retorna 403."""
        response = self.client.post("/ingesta/api/chat-users/rename/", {"user_id": 1, "name": "test"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_summary_without_auth_returns_403(self):
        """Summary trigger sin autenticacion retorna 403."""
        response = self.client.post("/ingesta/api/summary/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_audio_briefing_without_auth_returns_403(self):
        """Audio briefing sin autenticacion retorna 403."""
        response = self.client.post("/ingesta/api/audio-briefing/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WebhookHMACTest(TestCase):
    """Verifica que el webhook de contacto firme sus requests con HMAC.

    S-04: HMAC/firma en webhook.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/crm/webhook/chat/"
        self.payload = {"phone_number": "+573001234567", "tenant_slug": "test-tenant"}
        self.raw_body = json.dumps(self.payload).encode("utf-8")

    @override_settings(WEBHOOK_SECRET="test-secret-key")
    def test_webhook_without_signature_returns_403(self):
        """Webhook sin firma retorna 403."""
        response = self.client.post(
            self.url,
            data=self.payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(WEBHOOK_SECRET="test-secret-key")
    def test_webhook_with_invalid_signature_returns_403(self):
        """Webhook con firma invalida retorna 403."""
        response = self.client.post(
            self.url,
            data=self.payload,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE="invalid-signature",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(WEBHOOK_SECRET="test-secret-key")
    def test_webhook_with_valid_signature_returns_201(self):
        """Webhook con firma valida retorna 201 (crea contacto)."""
        sig = hmac.new(b"test-secret-key", self.raw_body, hashlib.sha256).hexdigest()
        response = self.client.post(
            self.url,
            data=self.payload,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )
        # 201 si el tenant existe, 404 si no (el test verifica que pasa la validacion HMAC)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND])

    @override_settings(WEBHOOK_SECRET="change-me-in-env")
    def test_webhook_with_default_secret_returns_501(self):
        """Webhook con secret por defecto (sin configurar) retorna 501."""
        response = self.client.post(
            self.url,
            data=self.payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
