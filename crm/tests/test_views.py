"""Pruebas de API y vistas HTML para la app `crm`.

Estas pruebas cubren los endpoints JSON de contactos, leads, estadisticas y
resumenes IA, ademas de las vistas HTML del dashboard Kanban y el detalle de
lead del CRM, validando el comportamiento observable de la capa de interfaces.
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, Client
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from tenants.domain.models import Tenant, PipelineConfig
from crm.domain.models import Contact, Lead, LeadSource, LeadActivity, LeadTask, Department, City


class CRMAPITestCase(TestCase):
    """Caso de prueba de la API CRM con datos base compartidos."""

    def setUp(self):
        """Construye un tenant y un contacto minimo para las pruebas."""

        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
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

    def test_analytics_api_reflects_seed_sources(self):
        """Valida que las fuentes de leads aparezcan correctamente en analytics."""
        dept = Department.objects.create(name="Cundinamarca")
        city = City.objects.create(department=dept, name="Bogotá")
        contact = Contact.objects.create(
            tenant=self.tenant, full_name="Test Meta", phone_number="573001111111", city=city
        )
        contact2 = Contact.objects.create(
            tenant=self.tenant, full_name="Test Google", phone_number="573002222222", city=city
        )
        for i, (c, platform) in enumerate([(contact, "meta"), (contact2, "google")]):
            lead = Lead.objects.create(tenant=self.tenant, contact=c, current_stage="Lead")
            LeadSource.objects.create(lead=lead, platform=platform, utm_source=platform)

        response = self.client.get("/api/crm/tenants/codensolar/analytics/?days=365")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["summary"]["total_leads"], 2)
        sources = {row["source"] for row in response.data["leads_by_source"]}
        self.assertIn("meta", sources)
        self.assertIn("google", sources)

    def test_stage_change_creates_activity(self):
        """Valida que un cambio de etapa registre actividad en el historial."""

        PipelineConfig.objects.create(
            tenant=self.tenant,
            stages=[
                {"name": "Lead", "color": "#003366", "order": 1},
                {"name": "Cotización Enviada", "color": "#FF9933", "order": 2},
                {"name": "Cerrado Ganado", "color": "#00CC66", "order": 3},
            ],
            allow_skip_stages=True,
        )
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
        self.assertFalse(lead.is_closed)  # No es la última etapa, no se cierra

    def test_stage_change_to_last_closes_lead(self):
        """Valida que al llegar a la última etapa el lead se cierre como won."""

        PipelineConfig.objects.create(
            tenant=self.tenant,
            stages=[
                {"name": "Lead", "color": "#003366", "order": 1},
                {"name": "Cerrado Ganado", "color": "#00CC66", "order": 2},
            ],
            allow_skip_stages=True,
        )
        lead = Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        response = self.client.patch(
            f"/api/crm/leads/{lead.id}/?tenant_slug=codensolar",
            {"current_stage": "Cerrado Ganado"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.current_stage, "Cerrado Ganado")
        self.assertTrue(lead.is_closed)
        self.assertEqual(lead.closed_result, "won")

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

    def test_add_note_endpoint(self):
        """Valida que add_note cree una actividad tipo nota."""

        lead = Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        response = self.client.post(
            f"/api/crm/leads/{lead.id}/add_note/?tenant_slug=codensolar",
            {"note": "Cliente interesado en paneles solares"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity = lead.activities.filter(activity_type="note_added").first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.description, "Cliente interesado en paneles solares")

    def test_add_note_missing_field(self):
        """Valida que add_note acepte nota vacía (devuelve 201)."""

        lead = Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        response = self.client.post(
            f"/api/crm/leads/{lead.id}/add_note/?tenant_slug=codensolar",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_add_activity_endpoint(self):
        """Valida que add_activity cree una actividad tipo manual."""

        lead = Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        response = self.client.post(
            f"/api/crm/leads/{lead.id}/add_activity/?tenant_slug=codensolar",
            {"description": "Llamada de seguimiento realizada"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity = lead.activities.filter(activity_type="manual").first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.description, "Llamada de seguimiento realizada")

    def test_add_activity_missing_field(self):
        """Valida que add_activity devuelva 400 si falta 'description'."""

        lead = Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        response = self.client.post(
            f"/api/crm/leads/{lead.id}/add_activity/?tenant_slug=codensolar",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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

        client = Client()
        client.force_login(self.user)
        response = client.get("/crm/codensolar/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Codensolar SAS")
        self.assertContains(response, "Pipeline de Ventas")
        self.assertContains(response, "crm/css/themes.css")
        self.assertContains(response, "crm/css/base_layout.css")
        self.assertContains(response, "crm/css/dashboard.css")
        self.assertContains(response, "crm/js/theme.js")
        self.assertContains(response, "crm/js/dashboard.js")
        self.assertContains(response, "bi-person-circle")
        self.assertContains(response, "Configuración")

        self.assertContains(response, 'id="sama-sidebar"')
        self.assertContains(response, 'id="sidebar-toggle-btn"')
        self.assertContains(response, 'id="kanban-board"')
        self.assertContains(response, 'id="lead-search"')
        self.assertContains(response, 'id="sidebar-tags-list"')
        self.assertContains(response, 'id="stage-filter-checkboxes"')
        self.assertContains(response, 'id="filter-source"')
        self.assertContains(response, 'id="apply-filters-btn"')
        self.assertContains(response, 'id="sidebar-overlay"')

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

        client = Client()
        client.force_login(self.user)
        response = client.get(f"/crm/codensolar/leads/{lead.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Juan Pérez")
        self.assertContains(response, "Panel Solar 450W")

    def test_analytics_html_renders(self):
        """Valida que la pagina HTML de analiticas cargue los archivos correctos."""

        client = Client()
        client.force_login(self.user)
        response = client.get("/crm/codensolar/analytics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "crm/css/themes.css")
        self.assertContains(response, "crm/css/base_layout.css")
        self.assertContains(response, "crm/css/dashboard.css")
        self.assertContains(response, "crm/css/analytics.css")
        self.assertContains(response, "crm/js/theme.js")
        self.assertContains(response, "crm/js/analytics.js")
        self.assertContains(response, "chart.js")

    def test_theme_toggle_button_exists(self):
        """Verifica que el boton de theme toggle esta presente en el HTML."""

        client = Client()
        client.force_login(self.user)
        response = client.get("/crm/codensolar/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, 'class="theme-toggle"')


    def test_analytics_leads_by_region(self):
        """Verifica que la API de analiticas devuelva datos de leads por region."""
        dept = Department.objects.create(name="Cundinamarca")
        city = City.objects.create(department=dept, name="Bogotá")
        contact = Contact.objects.create(
            tenant=self.tenant, full_name="Test", phone_number="573001111111", city=city
        )
        lead = Lead.objects.create(
            tenant=self.tenant, contact=contact, current_stage="Lead"
        )
        response = self.client.get("/api/crm/tenants/codensolar/analytics/?days=365")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("leads_by_region", response.data)
        region_data = response.data["leads_by_region"]
        self.assertIsInstance(region_data, list)
        self.assertTrue(len(region_data) >= 1)
        self.assertEqual(region_data[0]["department"], "Cundinamarca")
        self.assertEqual(region_data[0]["total"], 1)

    def test_analytics_leads_by_source_monthly(self):
        """Verifica que la API devuelva datos de leads por fuente y mes."""
        lead = Lead.objects.create(
            tenant=self.tenant, contact=self.contact, current_stage="Lead"
        )
        LeadSource.objects.create(
            lead=lead, platform="meta", utm_source="test"
        )
        response = self.client.get("/api/crm/tenants/codensolar/analytics/?days=365")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("leads_by_source_monthly", response.data)
        monthly_data = response.data["leads_by_source_monthly"]
        self.assertIsInstance(monthly_data, list)


class PipelineConfigViewTestCase(TestCase):
    """Pruebas para la vista de configuracion del pipeline."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass123"
        )
        self.tenant = Tenant.objects.create(
            name="Codensolar SAS",
            slug="codensolar",
            is_active=True,
        )
        self.pipeline = PipelineConfig.objects.create(
            tenant=self.tenant,
            stages=[
                {"name": "Lead", "color": "#003366", "order": 1},
                {"name": "Cotización Enviada", "color": "#FF9933", "order": 2},
            ],
            allow_skip_stages=True,
        )

    def test_config_page_renders(self):
        """Comprueba que la pagina de configuracion del pipeline responde 200."""

        client = Client()
        client.force_login(self.user)
        response = client.get("/crm/codensolar/config/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_config_page_contains_stages(self):
        """Comprueba que el contexto incluya las etapas del pipeline."""

        client = Client()
        client.force_login(self.user)
        response = client.get("/crm/codensolar/config/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("stages", response.context)
        self.assertEqual(len(response.context["stages"]), 2)
        self.assertEqual(response.context["stages"][0]["name"], "Lead")

    def test_config_page_requires_login(self):
        """Comprueba que la pagina redirige si no hay sesion."""

        client = Client()
        response = client.get("/crm/codensolar/config/")
        self.assertEqual(response.status_code, 302)