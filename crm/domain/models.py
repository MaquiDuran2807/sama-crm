from django.db import models
from tenants.models import Tenant  # Asume que la app tenants ya está instalada


class Contact(models.Model):
    """Cliente final de un tenant (ej: Juan Pérez)."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="contacts")
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=32, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Origen del contacto
    utm_source = models.CharField(max_length=50, blank=True)
    utm_medium = models.CharField(max_length=50, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    referrer_contact = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referred_contacts")

    # Datos personalizados (definidos por el tenant en CustomField)
    custom_fields = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "phone_number"]),
            models.Index(fields=["tenant", "email"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.phone_number or self.email or 'sin contacto'})"


class LeadManager(models.Manager):
    """Manager que excluye leads marcados como eliminados."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class LeadQuerySet(models.QuerySet):
    """QuerySet personalizado con métodos de consulta para leads."""

    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def closed(self):
        return self.filter(is_closed=True)


class Lead(models.Model):
    """Oportunidad de venta. Un contacto puede tener varios leads."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="leads")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="leads")
    current_stage = models.CharField(max_length=100)
    product_of_interest = models.CharField(max_length=255, blank=True)
    product_category = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    skipped_stages = models.JSONField(default=list)
    is_closed = models.BooleanField(default=False)
    closed_result = models.CharField(max_length=20, blank=True)  # 'won' o 'lost'

    custom_fields = models.JSONField(default=dict)

    # ── Soft delete ──
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)

    objects = LeadManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "current_stage"]),
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["contact", "-created_at"]),
            models.Index(fields=["is_deleted"]),
            models.Index(fields=["deleted_at"]),
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Lead {self.id} - {self.contact.full_name} ({self.current_stage})"


class LeadSource(models.Model):
    """Origen del lead con detalle de UTM y plataforma."""
    class Platform(models.TextChoices):
        META = "meta", "Meta (Facebook/Instagram)"
        GOOGLE = "google", "Google Ads"
        TIKTOK = "tiktok", "TikTok"
        WEB = "web", "Página web"
        REFERRAL = "referral", "Referido"

    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name="source")
    platform = models.CharField(max_length=20, choices=Platform.choices, default=Platform.WEB)
    utm_source = models.CharField(max_length=50, blank=True)
    utm_medium = models.CharField(max_length=50, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    referrer_contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL, related_name="referred_leads")
    landing_page_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    PLATFORM_ICONS = {
        "meta": "bi-facebook",
        "google": "bi-google",
        "tiktok": "bi-tiktok",
        "web": "bi-globe",
        "referral": "bi-person-lines-fill",
    }

    def get_icon_class(self) -> str:
        """Retorna la clase del icono Bootstrap correspondiente a la plataforma."""
        return self.PLATFORM_ICONS.get(self.platform, "bi-globe")

    def __str__(self):
        return f"Fuente de {self.lead}"


class LeadActivity(models.Model):
    """Historial de actividades sobre un lead."""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=50, help_text="stage_change, note_added, auto_advance, etc.")
    description = models.TextField()
    performed_by = models.CharField(max_length=100, default="system")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.activity_type} en {self.lead} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"