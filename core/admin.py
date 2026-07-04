"""Configuración del admin para la app core."""

from django.contrib import admin
from core.domain.models import SiteConfiguration, Page, Section, MenuItem, ContactMessage


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    """Admin para SiteConfiguration."""

    list_display = ["tenant", "is_published", "updated_at"]
    list_filter = ["is_published", "tenant"]
    search_fields = ["tenant__name"]


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1
    ordering = ["order"]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    """Admin para Page."""

    list_display = ["title", "tenant", "status", "order", "is_featured", "updated_at"]
    list_filter = ["status", "tenant", "is_featured"]
    search_fields = ["title", "slug"]
    ordering = ["tenant", "order"]
    inlines = [SectionInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    """Admin para Section."""

    list_display = ["page", "section_type", "title", "order"]
    list_filter = ["section_type", "page__tenant"]
    search_fields = ["title", "page__title"]
    ordering = ["page", "order"]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin para MenuItem."""

    list_display = ["title", "tenant", "parent", "order", "is_visible"]
    list_filter = ["tenant", "is_visible"]
    search_fields = ["title"]
    ordering = ["tenant", "order"]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """Admin para ContactMessage."""

    list_display = ["name", "email", "tenant", "status", "created_at"]
    list_filter = ["status", "tenant", "created_at"]
    search_fields = ["name", "email", "message"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]