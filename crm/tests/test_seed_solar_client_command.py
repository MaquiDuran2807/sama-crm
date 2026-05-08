"""Pruebas del comando de seeding `seed_solar_client`.

Estas pruebas verifican que el comando cree el dataset base del cliente solar,
incluyendo tenant, pipeline, campos personalizados, contactos, leads y
resumenes IA iniciales.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from crm.models import Contact, Lead
from ingesta.models import ChatUser, DailyTextSummary
from tenants.models import CustomField, PipelineConfig, Tenant


@pytest.mark.django_db
def test_seed_solar_client_creates_expected_records() -> None:
    """Valida que el comando cree el dataset base de Codensolar."""

    out = StringIO()
    call_command("seed_solar_client", stdout=out)
    output = out.getvalue()

    tenant = Tenant.objects.get(slug="codensolar")
    assert tenant.name == "Codensolar SAS"
    assert tenant.tier == "pro"
    assert tenant.period == "quarterly"
    assert tenant.is_active is True
    assert tenant.subscription_start is not None
    assert tenant.subscription_end is not None

    pipeline = PipelineConfig.objects.get(tenant=tenant)
    assert len(pipeline.stages) == 6
    assert [stage["name"] for stage in pipeline.stages] == [
        "Lead",
        "Calificacion",
        "Cotizacion Enviada",
        "Seguimiento",
        "Cerrado Ganado",
        "Cerrado Perdido",
    ]

    custom_field_names = set(
        CustomField.objects.filter(tenant=tenant).values_list("field_name", flat=True)
    )
    assert {"tipo_cliente", "consumo_kwh", "fecha_instalacion"}.issubset(custom_field_names)

    assert Contact.objects.filter(tenant=tenant).count() == 5
    assert Lead.objects.filter(tenant=tenant).count() == 8

    chat_users = ChatUser.objects.filter(
        phone_number__in=["+573001112233", "+573002223344", "+573003334455"]
    )
    assert chat_users.count() == 3
    assert DailyTextSummary.objects.filter(user__in=chat_users).count() == 3

    assert "Seed completado: seed_solar_client" in output
    assert "- Contacts creados: 5" in output
    assert "- Leads creados: 8" in output
    assert "- DailyTextSummary creados: 3" in output
