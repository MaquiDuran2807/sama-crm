"""Pruebas de configuracion del admin para la app `crm`.

Valida que la administracion exponga la experiencia operativa esperada para
contactos, leads y su historial de actividades.
"""

import pytest
from django.contrib.admin.sites import site

from crm.admin import ContactAdmin, LeadActivityReadOnlyInline, LeadAdmin
from crm.models import Contact, Lead


@pytest.mark.django_db
def test_contact_admin_search_fields() -> None:
    """Valida busqueda por telefono y correo en ContactAdmin."""

    admin_instance = site._registry[Contact]
    assert isinstance(admin_instance, ContactAdmin)
    assert admin_instance.search_fields == ("phone_number", "email")


@pytest.mark.django_db
def test_lead_admin_filters_and_activity_inline() -> None:
    """Valida filtros requeridos e inline de solo lectura en LeadAdmin."""

    admin_instance = site._registry[Lead]
    assert isinstance(admin_instance, LeadAdmin)
    assert admin_instance.list_filter == ("tenant", "current_stage", "is_closed")
    assert LeadActivityReadOnlyInline in admin_instance.inlines
    inline_instance = LeadActivityReadOnlyInline(Lead, site)
    assert inline_instance.readonly_fields == (
        "activity_type",
        "description",
        "performed_by",
        "created_at",
    )
