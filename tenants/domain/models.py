from django.db import models

class SubscriptionTier(models.TextChoices):
    BASICO = "basico", "Básico"
    PRO = "pro", "Pro"
    FULL = "full", "Full"

class SubscriptionPeriod(models.TextChoices):
    MONTHLY = "monthly", "Mensual"
    QUARTERLY = "quarterly", "Trimestral"

class Tenant(models.Model):
    """Cliente de SAMA (ej: Codensolar SAS)."""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    blueprint = models.JSONField(default=dict, help_text="Configuración general del cliente")

    # Suscripción
    tier = models.CharField(max_length=20, choices=SubscriptionTier.choices, default=SubscriptionTier.BASICO)
    period = models.CharField(max_length=20, choices=SubscriptionPeriod.choices, default=SubscriptionPeriod.QUARTERLY)
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TenantModule(models.Model):
    """Módulo activo para un tenant."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="modules")
    module_key = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["tenant", "module_key"]

    def __str__(self):
        return f"{self.tenant.name} / {self.module_key}"


class PipelineConfig(models.Model):
    """Configuración del pipeline de ventas de un tenant."""
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="pipeline_config")
    stages = models.JSONField(default=list, help_text="Lista de etapas: [{name, color, order}]")
    allow_skip_stages = models.BooleanField(default=True)

    def __str__(self):
        return f"Pipeline de {self.tenant.name}"


class CustomField(models.Model):
    """Campo personalizado definido por un tenant para sus contactos o leads."""
    class TargetModel(models.TextChoices):
        CONTACT = "contact", "Contacto"
        LEAD = "lead", "Lead"

    class FieldType(models.TextChoices):
        TEXT = "text", "Texto"
        NUMBER = "number", "Número"
        DATE = "date", "Fecha"
        SELECT = "select", "Selección"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="custom_fields")
    target_model = models.CharField(max_length=10, choices=TargetModel.choices, default=TargetModel.CONTACT)
    field_name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=10, choices=FieldType.choices, default=FieldType.TEXT)
    options = models.JSONField(default=list, help_text="Opciones si es tipo select")
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["tenant", "target_model", "order"]

    def __str__(self):
        return f"{self.tenant.name} / {self.target_model} / {self.field_name}"