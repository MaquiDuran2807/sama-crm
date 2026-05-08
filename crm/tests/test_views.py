"""Pruebas de API y vistas HTML para la app `crm`.

Estas pruebas cubren los endpoints JSON de contactos, leads, estadisticas y
resumenes IA, ademas de las vistas HTML del dashboard Kanban y el detalle de
lead del CRM, validando el comportamiento observable de la capa de interfaces.
"""

from django.test import TestCase, Client
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from tenants.domain.models import Tenant, PipelineConfig
from crm.domain.models import Contact, Lead, LeadSource, LeadActivity


class CRMAPITestCase(TestCase):
    """Caso de prueba de la API CRM con datos base compartidos."""

    def setUp(self):
        """Construye un tenant y un contacto minimo para las pruebas."""

        self.client = APIClient()
        self.tenant = Tenant.objects.create(
            name="Codensolar SAS", slug="codensolar", is_active=True
        )
        self.contact = Contact.objects.create(
            tenant=self.tenant, full_name="Juan Pérez", phone_number="573001234567"
        )

    def test_list_contacts(self):
        """Valida que el listado de contactos respete el tenant filtrado."""

        response = self.client.get("/api/crm/contacts/?tenant_slug=codensolar")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_contact(self):
        """Valida la creacion de un contacto asociado al tenant."""

        response = self.client.post(
            "/api/crm/contacts/?tenant_slug=codensolar",
            {"full_name": "María Gómez", "phone_number": "573007654321"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Contact.objects.count(), 2)

    def test_list_leads(self):
        """Valida que el listado de leads devuelva los registros del tenant."""

        Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        response = self.client.get("/api/crm/leads/?tenant_slug=codensolar")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_lead_with_source(self):
        """Valida la creacion de un lead y su fuente de origen asociada."""

        response = self.client.post(
            "/api/crm/leads/?tenant_slug=codensolar",
            {
                "contact": self.contact.id,
                "current_stage": "Lead",
                "product_of_interest": "Panel Solar 450W",
                "utm_source": "facebook",
                "platform": "meta",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lead = Lead.objects.first()
        self.assertEqual(lead.product_of_interest, "Panel Solar 450W")
        self.assertTrue(hasattr(lead, "source"))
        self.assertEqual(lead.source.platform, "meta")

    def test_stage_change_creates_activity(self):
        """Valida que un cambio de etapa registre actividad en el historial."""

        lead = Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        response = self.client.patch(
            f"/api/crm/leads/{lead.id}/?tenant_slug=codensolar",
            {"current_stage": "Cotización Enviada"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.current_stage, "Cotización Enviada")
        self.assertTrue(lead.activities.filter(activity_type="stage_change").exists())

    def test_stats_endpoint(self):
        """Valida que el endpoint de estadisticas agregue el pipeline completo."""

        Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Cotización Enviada"
        )
        response = self.client.get("/api/crm/leads/stats/?tenant_slug=codensolar")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_leads"], 2)
        self.assertEqual(response.data["leads_nuevos_hoy"], 2)

    def test_summary_endpoint_no_data(self):
        """Valida la respuesta 404 cuando el lead no tiene resumen IA."""

        lead = Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        response = self.client.get(f"/api/crm/leads/{lead.id}/summary/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_dashboard_html_renders(self):
        """Valida que el dashboard HTML de CRM renderice para un tenant."""

        PipelineConfig.objects.create(
            tenant=self.tenant,
            stages=[
                {"name": "Lead", "color": "#003366", "order": 1},
                {"name": "Calificacion", "color": "#FF9933", "order": 2},
            ],
            allow_skip_stages=True,
        )
        Lead.objects.create(tenant=self.tenant, contact=self.contact, current_stage="Lead")

        response = Client().get("/crm/codensolar/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Codensolar SAS")
        self.assertContains(response, "Pipeline de Ventas")

    def test_lead_detail_html_renders(self):
        """Valida que el detalle HTML de lead renderice para un lead dado."""

        PipelineConfig.objects.create(
            tenant=self.tenant,
            stages=[
                {"name": "Lead", "color": "#003366", "order": 1},
            ],
            allow_skip_stages=True,
        )
        lead = Lead.objects.create(
            tenant=self.tenant,
            contact=self.contact,
            current_stage="Lead",
            product_of_interest="Panel Solar 450W",
        )

        response = Client().get(f"/crm/codensolar/leads/{lead.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Juan Pérez")
        self.assertContains(response, "Panel Solar 450W")