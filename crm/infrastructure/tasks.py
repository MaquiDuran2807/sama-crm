"""Tareas asíncronas (Celery) para la app CRM.

Este módulo concentra todas las tareas de larga duración o programadas
asociadas al CRM: avance automático de leads estancados, purga de leads
eliminados temporalmente, etc.

La arquitectura hexagonal exige que las tareas solo operen a través de
servicios de dominio (nunca directamente sobre modelos desde aquí),
garantizando que toda la lógica de negocio fluya por los canales
autorizados.
"""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from crm.domain.models import Lead


@shared_task(name="crm.tasks.auto_advance_stale_leads")
def auto_advance_stale_leads(tenant_id: int) -> dict[str, int]:
    """Avanza los leads estancados de un tenant.

    Args:
        tenant_id: PK del tenant sobre el que ejecutar el avance.

    Returns:
        Diccionario con la cantidad de leads avanzada.
    """
    from tenants.domain.models import Tenant
    from crm.domain.services import auto_advance_eligible_leads

    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except Tenant.DoesNotExist:
        return {"advanced": 0, "error": "Tenant no encontrado"}

    advanced_qs = auto_advance_eligible_leads(tenant)
    count = advanced_qs.count()
    return {"advanced": count}


@shared_task(name="crm.tasks.permanently_delete_old_leads")
def permanently_delete_old_leads() -> dict[str, int]:
    """Elimina definitivamente los leads en papelera de más de 30 días.

    Esta tarea debe ejecutarse diariamente via Celery Beat (por ejemplo,
    a las 3:00 AM). Los leads cuyo ``deleted_at`` sea anterior a
    ``timezone.now() - timedelta(days=30)`` se borran de la base de
    datos de forma irreversible.

    Returns:
        Diccionario con la cantidad de leads eliminados.
    """
    threshold = timezone.now() - timedelta(days=30)
    deleted_leads = Lead.all_objects.filter(
        is_deleted=True,
        deleted_at__lt=threshold,
    )
    count = deleted_leads.count()
    deleted_leads.delete()
    return {"permanently_deleted": count}