"""Señales para la app CRM.

Conecta eventos del modelo DailyTextSummary (app ingesta) con la invalidación
de caché de ``get_lead_summary`` para mantener los datos frescos.
"""

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ingesta.models import DailyTextSummary


@receiver([post_save, post_delete], sender=DailyTextSummary)
def invalidate_lead_summary_cache(sender, instance, **kwargs):
    """Invalida la caché de ``get_lead_summary`` para todos los leads cuyo
    contacto tenga el mismo número de teléfono que el ChatUser del resumen.

    Se ejecuta después de guardar o eliminar un DailyTextSummary.
    """
    chat_user = instance.user
    phone = chat_user.phone_number
    if not phone:
        return

    from crm.domain.models import Lead

    lead_ids = Lead.objects.filter(
        contact__phone_number=phone,
    ).values_list("id", flat=True)

    for lead_id in lead_ids:
        cache.delete(f"lead_summary_{lead_id}")
