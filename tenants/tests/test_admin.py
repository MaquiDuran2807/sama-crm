"""Pruebas de configuracion del admin para la app `tenants`.

Se valida que la configuracion administrativa exponga los campos, filtros e
inlines requeridos por el bloque funcional del proyecto.
"""

import pytest
from django.contrib.admin.sites import site

from tenants.admin import PipelineConfigInline, TenantAdmin, TenantModuleInline
from tenants.models import Tenant


@pytest.mark.django_db
def test_tenant_admin_configuration() -> None:
    """Valida list_display, list_filter e inlines requeridos para TenantAdmin."""

    admin_instance = site._registry[Tenant]
    assert isinstance(admin_instance, TenantAdmin)
    assert admin_instance.list_display == ("name", "tier", "period", "is_active", "slug")
    assert admin_instance.list_filter == ("tier", "is_active")
    inline_models = tuple(inline.model for inline in admin_instance.inlines)
    assert TenantModuleInline.model in inline_models
    assert PipelineConfigInline.model in inline_models
