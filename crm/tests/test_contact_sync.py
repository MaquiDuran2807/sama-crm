"""Pruebas para el servicio de sincronización de contactos.

Valida que ``sync_contact_from_whatsapp`` cree/actualice correctamente
ChatUser (ingesta) y Contact (crm) a partir de un número de teléfono,
así como el endpoint webhook ``/api/crm/webhook/chat/``.
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from tenants.domain.models import Tenant
from crm.domain.models import Contact
from crm.domain.contact_sync import sync_contact_from_whatsapp
from ingesta.models import ChatUser


class ContactSyncTestCase(TestCase):
    """Pruebas unitarias del servicio ``sync_contact_from_whatsapp``."""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Codensolar SAS", slug="codensolar", is_active=True
        )

    def test_creates_both_chatuser_and_contact(self):
        """Crea un ChatUser y Contact cuando no existen."""
        contact = sync_contact_from_whatsapp(
            self.tenant, "573001234567", "Juan Pérez"
        )
        assert Contact.objects.count() == 1
        assert ChatUser.objects.count() == 1
        assert contact.full_name == "Juan Pérez"
        assert contact.phone_number == "573001234567"
        assert contact.tenant == self.tenant

    def test_reuses_existing_chatuser(self):
        """Reusa un ChatUser existente con el mismo número."""
        ChatUser.objects.create(
            phone_number="573001234567", name="Juan Pérez", wa_id="573001234567"
        )
        contact = sync_contact_from_whatsapp(
            self.tenant, "573001234567", "Juan Pérez"
        )
        assert ChatUser.objects.count() == 1
        assert contact.full_name == "Juan Pérez"

    def test_reuses_existing_contact(self):
        """Reusa un Contact existente con el mismo tenant y número."""
        existing = Contact.objects.create(
            tenant=self.tenant,
            phone_number="573001234567",
            full_name="Juan Pérez",
        )
        contact = sync_contact_from_whatsapp(
            self.tenant, "573001234567", "Juan Pérez"
        )
        assert Contact.objects.count() == 1
        assert contact.pk == existing.pk

    def test_updates_chatuser_name_if_provided(self):
        """Actualiza el nombre del ChatUser si se proporciona uno nuevo."""
        ChatUser.objects.create(
            phone_number="573001234567", name="Antiguo", wa_id="573001234567"
        )
        sync_contact_from_whatsapp(self.tenant, "573001234567", "Juan Pérez")
        updated = ChatUser.objects.get(phone_number="573001234567")
        assert updated.name == "Juan Pérez"

    def test_updates_contact_name_if_blank(self):
        """Actualiza el full_name del Contact si estaba vacío."""
        Contact.objects.create(
            tenant=self.tenant, phone_number="573001234567", full_name=""
        )
        sync_contact_from_whatsapp(self.tenant, "573001234567", "Juan Pérez")
        updated = Contact.objects.get(phone_number="573001234567")
        assert updated.full_name == "Juan Pérez"

    def test_does_not_overwrite_contact_name(self):
        """No sobrescribe el nombre de un Contact que ya tiene nombre."""
        Contact.objects.create(
            tenant=self.tenant,
            phone_number="573001234567",
            full_name="Nombre Original",
        )
        sync_contact_from_whatsapp(self.tenant, "573001234567", "Nuevo Nombre")
        updated = Contact.objects.get(phone_number="573001234567")
        assert updated.full_name == "Nombre Original"


class WebhookSyncContactAPITestCase(TestCase):
    """Pruebas del endpoint ``POST /api/crm/webhook/chat/``."""

    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(
            name="Codensolar SAS", slug="codensolar", is_active=True
        )

    def test_webhook_creates_contact(self):
        """Crea un contacto vía webhook."""
        response = self.client.post(
            "/api/crm/webhook/chat/",
            {
                "phone_number": "573001234567",
                "tenant_slug": "codensolar",
                "full_name": "Juan Pérez",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["phone_number"], "573001234567")
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(ChatUser.objects.count(), 1)

    def test_webhook_reuses_existing(self):
        """Reusa un contacto existente (no duplica)."""
        Contact.objects.create(
            tenant=self.tenant,
            phone_number="573001234567",
            full_name="Juan Pérez",
        )
        response = self.client.post(
            "/api/crm/webhook/chat/",
            {
                "phone_number": "573001234567",
                "tenant_slug": "codensolar",
                "full_name": "Juan Pérez",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Contact.objects.count(), 1)

    def test_webhook_missing_phone_number(self):
        """Devuelve 400 si falta phone_number."""
        response = self.client.post(
            "/api/crm/webhook/chat/",
            {"tenant_slug": "codensolar"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_missing_tenant_slug(self):
        """Devuelve 400 si falta tenant_slug."""
        response = self.client.post(
            "/api/crm/webhook/chat/",
            {"phone_number": "573001234567"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_invalid_tenant(self):
        """Devuelve 404 si tenant_slug no existe."""
        response = self.client.post(
            "/api/crm/webhook/chat/",
            {
                "phone_number": "573001234567",
                "tenant_slug": "no-existe",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
