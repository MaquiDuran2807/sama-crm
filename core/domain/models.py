"""Modelos de dominio para la app core.

Contiene los modelos relacionados con el sitio web principal de SAMA,
incluyendo páginas, secciones, configuración visual y contenido estático.
"""

from django.db import models
from django.utils import timezone
from django.conf import settings


class SiteConfiguration(models.Model):
    """Configuración global del sitio web."""

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="site_config",
    )

    logo_url = models.URLField(blank=True)
    favicon_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, default="#2563eb")
    secondary_color = models.CharField(max_length=7, default="#64748b")

    hero_title = models.CharField(max_length=255, default="Bienvenido a SAMA")
    hero_subtitle = models.TextField(blank=True)
    hero_cta_text = models.CharField(max_length=100, default="Contáctanos")
    hero_cta_url = models.CharField(max_length=255, default="/contact/")

    footer_text = models.TextField(blank=True)
    footer_links = models.JSONField(default=list)

    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    contact_address = models.TextField(blank=True)

    social_links = models.JSONField(default=dict)

    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.TextField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    is_published = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Configuración del sitio"
        verbose_name_plural = "Configuraciones del sitio"

    def __str__(self):
        return f"Configuración - {self.tenant.name}"


class Page(models.Model):
    """Página del sitio web."""

    class PageStatus(models.TextChoices):
        DRAFT = "draft", "Borrador"
        PUBLISHED = "published", "Publicado"
        ARCHIVED = "archived", "Archivado"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="pages",
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=PageStatus.choices,
        default=PageStatus.DRAFT,
    )

    content = models.TextField(blank=True)
    template_name = models.CharField(max_length=100, default="default")

    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.TextField(max_length=160, blank=True)

    order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order", "-created_at"]
        unique_together = ["tenant", "slug"]

    def __str__(self):
        return f"{self.title} ({self.tenant.name})"


class Section(models.Model):
    """Sección dentro de una página."""

    class SectionType(models.TextChoices):
        HERO = "hero", "Hero/Banner"
        TEXT = "text", "Texto"
        IMAGE = "image", "Imagen"
        VIDEO = "video", "Video"
        CTA = "cta", "Llamada a la acción"
        TESTIMONIAL = "testimonial", "Testimonio"
        FEATURES = "features", "Características"
        FAQ = "faq", "Preguntas frecuentes"
        FORM = "form", "Formulario"

    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    section_type = models.CharField(max_length=20, choices=SectionType.choices)
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)

    image_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)

    config = models.JSONField(default=dict)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.get_section_type_display()} - {self.page.title}"


class MenuItem(models.Model):
    """Elemento del menú de navegación."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="menu_items",
    )

    title = models.CharField(max_length=100)
    url = models.CharField(max_length=255)
    page = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="menu_items",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.title} ({self.tenant.name})"


class ContactMessage(models.Model):
    """Mensaje de contacto enviado desde el sitio web."""

    class Status(models.TextChoices):
        NEW = "new", "Nuevo"
        READ = "read", "Leído"
        REPLIED = "replied", "Respondido"
        ARCHIVED = "archived", "Archivado"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="contact_messages",
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Mensaje de {self.name} - {self.tenant.name}"