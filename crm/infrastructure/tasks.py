"""Tareas asíncronas (Celery) para la app CRM.

Este módulo concentra todas las tareas de larga duración o programadas
asociadas al CRM: avance automático de leads estancados, purga de leads
eliminados temporalmente, etc.

La arquitectura hexagonal exige que las tareas solo operen a través de
servicios de dominio (nunca directamente sobre modelos desde aquí),
garantizando que toda la lógica de negocio fluya por los canales
autorizados.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from crm.domain.models import Lead

logger = logging.getLogger(__name__)


@shared_task(name="crm.tasks.auto_advance_stale_leads")
def auto_advance_stale_leads() -> dict[str, int]:
    """Avanza los leads estancados de todos los tenants activos.

    Itera sobre todos los tenants activos y ejecuta el avance de leads
    estancados (último contacto > 48h) para cada uno.

    Returns:
        Diccionario con la cantidad total de leads avanzada.
    """
    from tenants.domain.models import Tenant
    from crm.domain.services import auto_advance_eligible_leads

    total_advanced = 0
    tenants = Tenant.objects.filter(is_active=True)
    for tenant in tenants:
        try:
            advanced_qs = auto_advance_eligible_leads(tenant)
            count = advanced_qs.count()
            if count:
                logger.info(
                    "auto_advance: tenant=%s (pk=%s) avanzó %s leads",
                    tenant.slug, tenant.pk, count,
                )
            total_advanced += count
        except Exception as exc:
            logger.exception(
                "auto_advance: error en tenant=%s (pk=%s): %s",
                tenant.slug, tenant.pk, exc,
            )

    return {"advanced": total_advanced}


@shared_task(name="crm.tasks.permanently_delete_old_leads")
def permanently_delete_old_leads() -> dict[str, int]:
    """Elimina definitivamente los leads en papelera de más de 30 días.

    Esta tarea debe ejecutarse diariamente via Celery Beat (por ejemplo,
    a las 3:00 AM). Los leads cuyo ``deleted_at`` sea anterior a
    ``timezone.now() - timedelta(days=30)`` se borran de la base de
    datos de forma irreversible.

    Uses ``transaction.atomic()`` para asegurar consistencia.

    Returns:
        Diccionario con la cantidad de leads eliminados.
    """
    threshold = timezone.now() - timedelta(days=30)
    with transaction.atomic():
        deleted_leads = Lead.all_objects.filter(
            is_deleted=True,
            deleted_at__lt=threshold,
        )
        count = deleted_leads.count()
        deleted_leads.delete()

    logger.info("permanently_delete_old_leads: %s leads eliminados", count)
    return {"permanently_deleted": count}


@shared_task(name="crm.tasks.send_task_reminders")
def send_task_reminders() -> str:
    """Revisa todas las tareas pendientes y registra recordatorios.

    Esta tarea busca tareas que:
    - No están completadas (is_completed=False)
    - Tienen fecha de vencimiento (due_date no es null)
    - Vencen hoy, mañana, o ya están vencidas
    - Pertenecen a leads no eliminados y no cerrados

    Returns:
        Mensaje con la cantidad de recordatorios procesados.
    """
    from crm.domain.models import LeadTask

    now = timezone.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    upcoming_tasks = LeadTask.objects.filter(
        is_completed=False,
        due_date__isnull=False,
        due_date__lte=tomorrow,
        lead__is_deleted=False,
        lead__is_closed=False,
    ).select_related("lead__contact", "lead__tenant")

    count = 0
    for task in upcoming_tasks:
        lead = task.lead
        days_until = (task.due_date - today).days if task.due_date else None
        if days_until is not None and days_until < 0:
            status = f"VENCIDA (hace {-days_until} días)"
        elif days_until == 0:
            status = "VENCE HOY"
        elif days_until == 1:
            status = "VENCE MAÑANA"
        else:
            status = f"Vence en {days_until} días"

        logger.info(
            "[TASK REMINDER] %s | Lead: %s | Tarea: %s | %s | Due: %s",
            lead.tenant.name,
            lead.contact.full_name,
            task.description,
            status,
            task.due_date,
        )
        count += 1

    logger.info("send_task_reminders: %s recordatorios procesados", count)
    return f"Se procesaron {count} recordatorios de tareas."