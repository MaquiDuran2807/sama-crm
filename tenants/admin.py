"""Configuracion del Django Admin para la app `tenants`.

Este archivo centraliza el registro de modelos administrativos que permiten
inspeccionar y editar la configuracion comercial de cada tenant desde el panel
de administracion. Incluye inlines para el pipeline y los modulos asociados.
"""

from django.contrib import admin

from tenants.models import CustomField, PipelineConfig, Tenant, TenantModule
from tenants.domain.models import TenantUser


class TenantModuleInline(admin.TabularInline):
    """Inline tabular para editar los modulos vinculados a un tenant.

    El formulario embebido muestra cada `TenantModule` asociado al tenant que
    se esta editando y permite administrar su estado sin salir de la ficha
    principal del cliente.
    """

    model = TenantModule
    extra = 0


class PipelineConfigInline(admin.StackedInline):
    """Inline apilado para editar la configuracion del pipeline del tenant.

    Se usa una sola configuracion por tenant (`OneToOneField`), por lo que se
    limita a un unico bloque embebido con `max_num=1`.
    """

    model = PipelineConfig
    extra = 0
    max_num = 1


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Ficha administrativa principal del tenant.

    Muestra los atributos operativos mas relevantes del cliente y embebe el
    pipeline y los modulos para mantener la edicion concentrada en una sola
    pantalla.
    """

    list_display = ("name", "tier", "period", "is_active", "slug")
    list_filter = ("tier", "is_active")
    search_fields = ("name", "slug")
    inlines = (TenantModuleInline, PipelineConfigInline)


@admin.register(TenantModule)
class TenantModuleAdmin(admin.ModelAdmin):
    """Listado administrativo de modulos configurados por tenant."""

    list_display = ("tenant", "module_key", "display_name", "is_active", "created_at")
    list_filter = ("is_active", "module_key")
    search_fields = ("tenant__name", "module_key", "display_name")


@admin.register(PipelineConfig)
class PipelineConfigAdmin(admin.ModelAdmin):
    """Vista administrativa para la configuracion del pipeline comercial."""

    list_display = ("tenant", "allow_skip_stages")
    list_filter = ("allow_skip_stages",)
    search_fields = ("tenant__name",)


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    """Vista administrativa para los campos personalizados del CRM."""

    list_display = ("tenant", "target_model", "field_name", "field_type", "is_required", "order")
    list_filter = ("target_model", "field_type", "is_required")
    search_fields = ("tenant__name", "field_name")


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    """Registro administrativo para asociar usuarios a tenants."""

    list_display = ("user", "tenant", "role", "created_at")
    list_filter = ("role", "tenant")
    search_fields = ("user__username", "tenant__name")
