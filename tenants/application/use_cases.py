from tenants.domain.models import Tenant, TenantModule, PipelineConfig
from tenants.domain.services import is_subscription_active, get_active_modules

class GetTenantModulesUseCase:
    """Caso de uso para obtener los módulos activos de un tenant."""
    def execute(self, tenant: Tenant):
        return get_active_modules(tenant)

class UpdatePipelineConfigUseCase:
    """Caso de uso para validar y actualizar la configuración del pipeline de ventas."""
    def execute(self, tenant: Tenant, stages_data: list) -> PipelineConfig:
        if not isinstance(stages_data, list):
            raise ValueError("Se requiere un array 'stages'.")
            
        validated_stages = []
        for idx, stage in enumerate(stages_data):
            name = stage.get("name", "").strip()
            if not name:
                raise ValueError(f"Etapa {idx + 1} no tiene nombre.")
            validated_stages.append({
                "name": name,
                "color": stage.get("color", "#003366").strip() or "#003366",
                "order": int(stage.get("order", idx + 1)),
            })
            
        from django.shortcuts import get_object_or_404
        pipeline_config = get_object_or_404(PipelineConfig, tenant=tenant)
        pipeline_config.stages = validated_stages
        pipeline_config.save(update_fields=["stages"])
        return pipeline_config

class ValidateSubscriptionUseCase:
    """Caso de uso para validar si la suscripción de un tenant está vigente."""
    def execute(self, tenant: Tenant) -> bool:
        return is_subscription_active(tenant)
