"""Serializadores de la capa de interfaces para la app `tenants`.

Estos serializadores traducen los modelos del dominio a representaciones JSON
consumibles por la API REST, y tambien definen la forma en que el frontend o
otros clientes pueden leer la configuracion de cada tenant.
"""

from rest_framework import serializers
from tenants.domain.models import Tenant, TenantModule, PipelineConfig, CustomField


class TenantModuleSerializer(serializers.ModelSerializer):
    """Representacion compacta de un modulo del tenant."""

    class Meta:
        model = TenantModule
        fields = ["id", "module_key", "display_name", "is_active", "config"]


class PipelineConfigSerializer(serializers.ModelSerializer):
    """Serializa la configuracion del pipeline comercial."""

    class Meta:
        model = PipelineConfig
        fields = ["stages", "allow_skip_stages"]


class CustomFieldSerializer(serializers.ModelSerializer):
    """Serializa la definicion de un campo personalizado del CRM."""

    class Meta:
        model = CustomField
        fields = ["id", "target_model", "field_name", "field_type", "options", "is_required", "order"]


class TenantSerializer(serializers.ModelSerializer):
    """Serializador resumido para listar tenants activos."""

    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "tier", "period", "is_active"]


class TenantDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado para el endpoint de detalle del tenant."""

    modules = TenantModuleSerializer(many=True, read_only=True)
    pipeline_config = PipelineConfigSerializer(read_only=True)
    custom_fields = CustomFieldSerializer(many=True, read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id", "name", "slug", "is_active", "blueprint",
            "tier", "period", "subscription_start", "subscription_end", "auto_renew",
            "modules", "pipeline_config", "custom_fields",
            "created_at", "updated_at",
        ]