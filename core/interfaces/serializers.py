"""Serializers para la app core."""

from rest_framework import serializers
from core.domain.models import SiteConfiguration, Page, Section, MenuItem, ContactMessage


class SiteConfigurationSerializer(serializers.ModelSerializer):
    """Serializer para SiteConfiguration."""

    class Meta:
        model = SiteConfiguration
        fields = [
            "tenant",
            "logo_url",
            "favicon_url",
            "primary_color",
            "secondary_color",
            "hero_title",
            "hero_subtitle",
            "hero_cta_text",
            "hero_cta_url",
            "footer_text",
            "footer_links",
            "contact_email",
            "contact_phone",
            "contact_address",
            "social_links",
            "meta_title",
            "meta_description",
            "meta_keywords",
            "is_published",
        ]


class SectionSerializer(serializers.ModelSerializer):
    """Serializer para Section."""

    section_type_display = serializers.CharField(source="get_section_type_display", read_only=True)

    class Meta:
        model = Section
        fields = [
            "id",
            "section_type",
            "section_type_display",
            "title",
            "content",
            "image_url",
            "video_url",
            "config",
            "order",
        ]


class PageSerializer(serializers.ModelSerializer):
    """Serializer para Page."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "title",
            "slug",
            "status",
            "status_display",
            "content",
            "template_name",
            "meta_title",
            "meta_description",
            "order",
            "is_featured",
            "sections",
            "created_at",
            "updated_at",
            "published_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "published_at"]


class PageListSerializer(serializers.ModelSerializer):
    """Serializer para listar páginas."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Page
        fields = ["id", "title", "slug", "status", "status_display", "order", "is_featured", "updated_at"]


class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer para MenuItem."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = ["id", "title", "url", "page", "parent", "order", "is_visible", "children"]

    def get_children(self, obj):
        return MenuItemSerializer(obj.children.filter(is_visible=True).order_by("order"), many=True).data


class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer para ContactMessage."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "status",
            "status_display",
            "ip_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "ip_address", "created_at", "updated_at"]


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear ContactMessage."""

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]