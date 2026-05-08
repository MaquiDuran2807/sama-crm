"""Configuracion del Django Admin para la app `crm`.

Este modulo registra la vista administrativa de contactos, leads, fuentes y
actividades para que el equipo comercial pueda inspeccionar el pipeline desde
el admin de Django sin salir del proyecto.
"""

from django.contrib import admin

from crm.models import Contact, Lead, LeadActivity, LeadSource


class LeadActivityReadOnlyInline(admin.TabularInline):
    """Inline de actividades del lead en modo solo lectura.

    Se usa para mostrar el historial de cambios sin permitir altas manuales
    desde el admin, preservando el registro cronologico que genera la logica
    de negocio.
    """

    model = LeadActivity
    extra = 0
    can_delete = False
    readonly_fields = ("activity_type", "description", "performed_by", "created_at")

    def has_add_permission(self, request, obj=None):
        """Deshabilita alta manual para mantener el historial inmutable desde admin."""

        return False


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Vista administrativa principal para los contactos CRM."""

    list_display = ("full_name", "tenant", "phone_number", "email", "city", "created_at")
    list_filter = ("tenant", "city")
    search_fields = ("phone_number", "email")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    """Vista administrativa principal para los leads del CRM."""

    list_display = ("id", "tenant", "contact", "current_stage", "is_closed", "updated_at")
    list_filter = ("tenant", "current_stage", "is_closed")
    search_fields = ("contact__full_name", "contact__phone_number", "contact__email")
    inlines = (LeadActivityReadOnlyInline,)


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    """Vista administrativa para la fuente/origen de los leads."""

    list_display = ("lead", "platform", "utm_source", "utm_medium", "utm_campaign", "created_at")
    list_filter = ("platform",)
    search_fields = ("lead__contact__full_name", "utm_source", "utm_campaign")


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    """Vista administrativa para revisar el historial de actividades."""

    list_display = ("lead", "activity_type", "performed_by", "created_at")
    list_filter = ("activity_type", "performed_by")
    search_fields = ("lead__contact__full_name", "description")
    readonly_fields = ("created_at",)
