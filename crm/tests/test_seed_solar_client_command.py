"""Pruebas del comando de seeding `seed_solar_client`.

Estas pruebas verifican que el comando cree el dataset base del cliente solar,
incluyendo tenant, pipeline, campos personalizados, contactos, leads y
reportes de seguimiento.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from crm.models import Contact, Lead, LeadActivity, LeadSource, DailyFollowupReport
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

    assert Contact.objects.filter(tenant=tenant).count() == 50
    assert Lead.objects.filter(tenant=tenant).count() >= 80
    assert LeadSource.objects.filter(lead__tenant=tenant).count() >= 80
    assert LeadActivity.objects.filter(lead__tenant=tenant).count() > 0

    source_platforms = set(
        LeadSource.objects.filter(lead__tenant=tenant).values_list("platform", flat=True)
    )
    assert source_platforms == {"meta", "google", "tiktok", "web", "referral"}

    assert DailyFollowupReport.objects.filter(tenant=tenant).count() == 3

    assert "Seed completado" in output
    assert "50 contactos creados" in output
    assert "Leads por etapa:" in output


@pytest.mark.django_db
def test_seed_solar_client_idempotente() -> None:
    """Verifica que el comando sea idempotente."""

    call_command("seed_solar_client", stdout=StringIO())

    count_contacts_1 = Contact.objects.count()
    count_leads_1 = Lead.all_objects.count()

    call_command("seed_solar_client", stdout=StringIO())

    count_contacts_2 = Contact.objects.count()
    count_leads_2 = Lead.all_objects.count()

    assert count_contacts_1 == count_contacts_2
    assert count_leads_1 == count_leads_2