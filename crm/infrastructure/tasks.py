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


@shared_task(name="crm.tasks.send_task_reminders")
def send_task_reminders() -> str:
    """Revisa todas las tareas pendientes y muestra recordatorios en consola.

    Esta tarea busca tareas que:
    - No están completadas (is_completed=False)
    - Tienen fecha de vencimiento (due_date no es null)
    - Vencen hoy, mañana, o ya están vencidas
    - Pertenecen a leads no eliminados y no cerrados

    En el futuro, esta tarea podría enviar notificaciones por WhatsApp
    al tenant o al usuario asignado.

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

        print(
            f"[TASK REMINDER] {lead.tenant.name} | Lead: {lead.contact.full_name} | "
            f"Tarea: {task.description} | {status} | Due: {task.due_date}"
        )
        count += 1

    return f"Se procesaron {count} recordatorios de tareas."