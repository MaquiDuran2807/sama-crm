from django.db import transaction
from django.utils import timezone
from crm.domain.models import Lead, LeadSource, LeadActivity
from crm.domain.services import change_lead_stage, create_reopen_lead
from tenants.domain.services import get_pipeline_stages

class CreateLeadUseCase:
    """Caso de uso para crear un lead y su fuente de origen asociada."""
    def execute(self, tenant, lead_data: dict, utm_data: dict, performed_by: str) -> Lead:
        with transaction.atomic():
            lead = Lead.objects.create(tenant=tenant, **lead_data)
            
            # Validar y crear LeadSource si hay datos de UTM
            if any(utm_data.values()):
                platform = utm_data.get("platform", "web")
                LeadSource.objects.create(
                    lead=lead,
                    platform=platform,
                    utm_source=utm_data.get("utm_source", ""),
                    utm_medium=utm_data.get("utm_medium", ""),
                    utm_campaign=utm_data.get("utm_campaign", ""),
                    landing_page_url=utm_data.get("landing_page_url", ""),
                    referrer_contact=utm_data.get("referrer_contact", None),
                )
            
            # Registrar actividad de creación
            LeadActivity.objects.create(
                lead=lead,
                activity_type="created",
                description="Lead creado",
                performed_by=performed_by,
            )
            return lead

class ChangeLeadStageUseCase:
    """Caso de uso para cambiar la etapa de un lead y actualizar su estado cerrado/abierto."""
    def execute(self, lead: Lead, old_stage: str, new_stage: str, performed_by: str) -> Lead:
        with transaction.atomic():
            if old_stage != new_stage:
                lead = change_lead_stage(lead, new_stage, performed_by=performed_by)
                
                new_stage_lower = new_stage.lower()
                if "cerrado" in new_stage_lower or "closed" in new_stage_lower:
                    lead.is_closed = True
                    if "ganado" in new_stage_lower or "won" in new_stage_lower:
                        lead.closed_result = "won"
                    elif "perdido" in new_stage_lower or "lost" in new_stage_lower:
                        lead.closed_result = "lost"
                    lead.save(update_fields=["is_closed", "closed_result", "updated_at"])
            return lead

class AddNoteUseCase:
    """Caso de uso para registrar una nota como actividad en el lead."""
    def execute(self, lead: Lead, note: str, performed_by: str) -> LeadActivity | None:
        note = (note or "").strip()
        if not note:
            return None
        return LeadActivity.objects.create(
            lead=lead,
            activity_type="note_added",
            description=note,
            performed_by=performed_by,
        )

class ReopenLeadUseCase:
    """Caso de uso para reabrir un lead cerrado (recompra) generando un nuevo lead en la primera etapa."""
    def execute(self, lead: Lead, performed_by: str) -> Lead:
        if not lead.is_closed:
            raise ValueError("El lead no está cerrado.")
            
        stages = get_pipeline_stages(lead.tenant)
        if not stages:
            raise ValueError("No hay etapas configuradas en el pipeline.")
            
        sorted_stages = sorted(stages, key=lambda s: s.get("order", 0))
        first_stage = sorted_stages[0].get("name", "")
        
        return create_reopen_lead(lead, first_stage, performed_by=performed_by)

class DeleteLeadUseCase:
    """Caso de uso para realizar soft delete del lead."""
    def execute(self, lead: Lead, performed_by: str) -> Lead:
        with transaction.atomic():
            lead.is_deleted = True
            lead.deleted_at = timezone.now()
            lead.deleted_by = performed_by
            lead.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
            
            LeadActivity.objects.create(
                lead=lead,
                activity_type="deleted",
                description="Lead enviado a papelera",
                performed_by=performed_by,
            )
            return lead

class AddActivityUseCase:
    """Caso de uso para registrar una actividad manual en el lead."""
    def execute(self, lead: Lead, description: str, performed_by: str) -> LeadActivity:
        return LeadActivity.objects.create(
            lead=lead,
            activity_type="manual",
            description=description,
            performed_by=performed_by,
        )

class RestoreLeadUseCase:
    """Caso de uso para restaurar un lead de la papelera (soft delete reversal)."""
    def execute(self, lead: Lead, performed_by: str) -> Lead:
        with transaction.atomic():
            lead.is_deleted = False
            lead.deleted_at = None
            lead.deleted_by = ""
            lead.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
            LeadActivity.objects.create(
                lead=lead,
                activity_type="restored",
                description="Lead restaurado de la papelera",
                performed_by=performed_by,
            )
            return lead
