"""Pruebas de API para la app `tenants`.

Estas pruebas validan que los endpoints REST del modulo de tenants sigan
devolviendo la estructura esperada para lista, detalle y acciones auxiliares
del pipeline, modulos y campos personalizados.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from tenants.domain.models import Tenant, TenantModule, PipelineConfig, CustomField


class TenantAPITestCase(TestCase):
    """Caso de prueba de la API de tenants con datos mínimos de referencia."""

    def setUp(self):
        """Prepara un tenant base con pipeline, modulo y campo personalizado."""

        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.tenant = Tenant.objects.create(
            name="Codensolar SAS",
            slug="codensolar",
            tier="pro",
            period="quarterly",
            is_active=True,
        )
        PipelineConfig.objects.create(
            tenant=self.tenant,
            stages=[
                {"name": "Lead", "color": "#003366", "order": 1},
                {"name": "Cotización Enviada", "color": "#FF9933", "order": 2},
                {"name": "Cerrado Ganado", "color": "#00CC66", "order": 3},
            ],
            allow_skip_stages=True,
        )
        TenantModule.objects.create(
            tenant=self.tenant, module_key="crm", display_name="CRM", is_active=True
        )
        CustomField.objects.create(
            tenant=self.tenant, target_model="contact", field_name="tipo_cliente",
            field_type="select", options=["Residencial", "Comercial"], order=1
        )

    def test_list_tenants(self):
        """Comprueba que el listado solo devuelva tenants activos."""

        response = self.client.get("/api/tenants/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], "codensolar")

    def test_retrieve_tenant(self):
        """Comprueba que el detalle incluya la configuracion relacionada."""

        response = self.client.get("/api/tenants/codensolar/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Codensolar SAS")
        self.assertIn("pipeline_config", response.data)

    def test_pipeline_endpoint(self):
        """Comprueba que el endpoint de pipeline entregue las etapas."""

        response = self.client.get("/api/tenants/codensolar/pipeline/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["stages"]), 3)

    def test_modules_endpoint(self):
        """Comprueba que el endpoint de modulos activos responda correctamente."""

        response = self.client.get("/api/tenants/codensolar/modules/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["module_key"], "crm")

    def test_custom_fields_endpoint(self):
        """Comprueba que el endpoint de campos personalizados filtre bien."""

        response = self.client.get("/api/tenants/codensolar/custom-fields/?target_model=contact")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["field_name"], "tipo_cliente")

    def test_inactive_tenant_not_listed(self):
        """Comprueba que un tenant inactivo desaparece del listado publico."""

        self.tenant.is_active = False
        self.tenant.save()
        response = self.client.get("/api/tenants/")
        self.assertEqual(len(response.data), 0)

    def test_update_pipeline(self):
        """Comprueba que PATCH actualiza las etapas del pipeline."""

        response = self.client.patch(
            "/api/tenants/codensolar/pipeline-config/",
            {"stages": [
                {"name": "Nuevo Lead", "color": "#003366", "order": 1},
                {"name": "Contactado", "color": "#FF9933", "order": 2},
                {"name": "Cerrado", "color": "#10b981", "order": 3},
            ]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["stages"]), 3)
        self.assertEqual(response.data["stages"][0]["name"], "Nuevo Lead")

    def test_update_pipeline_get(self):
        """Comprueba que GET del pipeline-config retorna las etapas."""

        response = self.client.get("/api/tenants/codensolar/pipeline-config/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["stages"]), 3)

    def test_update_pipeline_missing_name(self):
        """Comprueba que PATCH rechaza etapas sin nombre."""

        response = self.client.patch(
            "/api/tenants/codensolar/pipeline-config/",
            {"stages": [{"name": "", "color": "#003366", "order": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_pipeline_missing_stages(self):
        """Comprueba que PATCH rechaza cuando no hay array stages."""

        response = self.client.patch(
            "/api/tenants/codensolar/pipeline-config/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)