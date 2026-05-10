"""Pruebas de comandos de gestión de CRM."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from crm.models import Contact, Lead, LeadActivity, LeadSource
from tenants.models import Tenant


@pytest.mark.django_db
def test_reset_crm_data_elimina_leads_y_contactos() -> None:
    """Verifica que reset_crm_data elimine leads y contactos pero mantenga el tenant."""

    out = StringIO()
    call_command("seed_solar_client", stdout=out)

    assert Tenant.objects.count() > 0
    assert Lead.all_objects.count() > 0
    assert Contact.objects.count() > 0

    with patch("builtins.input", return_value="sí"):
        call_command("reset_crm_data", stdout=StringIO())

    assert Tenant.objects.count() == 1
    assert Contact.objects.count() == 0
    assert Lead.all_objects.count() == 0
    assert LeadSource.objects.count() == 0
    assert LeadActivity.objects.count() == 0


@pytest.mark.django_db
def test_reset_crm_data_con_confirmar() -> None:
    """Verifica que reset_crm_data --confirmar funcione sin interacción."""

    call_command("seed_solar_client", stdout=StringIO())

    call_command("reset_crm_data", "--confirmar", stdout=StringIO())

    assert Tenant.objects.count() == 1
    assert Lead.all_objects.count() == 0
    assert Contact.objects.count() == 0


@pytest.mark.django_db
def test_reset_crm_data_sin_datos_no_genera_error() -> None:
    """Verifica que reset_crm_data funcione cuando no hay datos."""

    out = StringIO()
    call_command("reset_crm_data", "--confirmar", stdout=out)

    assert "No había datos para eliminar" in out.getvalue()
    assert Lead.all_objects.count() == 0


@pytest.mark.django_db
def test_reset_crm_data_cancela_con_respuesta_negativa() -> None:
    """Verifica que el comando se cancele con respuesta diferente a 'sí'."""

    call_command("seed_solar_client", stdout=StringIO())

    with patch("builtins.input", return_value="no"):
        out = StringIO()
        call_command("reset_crm_data", stdout=out)

    assert "cancelada" in out.getvalue().lower()
    assert Lead.all_objects.count() > 0
    assert Contact.objects.count() > 0