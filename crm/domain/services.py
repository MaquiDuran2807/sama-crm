"""Servicios de dominio para la app CRM.

Este módulo concentra **toda la lógica de negocio pura** asociada a contactos,
leads, movimientos de etapa, cálculo de estadísticas y consulta de resúmenes de
IA relacionados con un lead.

.. attention::
   El dominio **nunca** importa desde las capas ``interfaces`` ni
   ``infrastructure``. Cualquier dependencia externa (HTTP, plantillas, colas
   de tareas) debe inyectarse desde fuera o ser invocada únicamente por los
   casos de uso de la capa ``application``.

Contexto dentro del sistema
----------------------------
Estos servicios son consumidos directamente por:

* Las vistas de la API REST (``crm.interfaces.views``).
* Las tareas asíncronas de Celery (``crm.infrastructure.tasks``).
* Los casos de uso de la capa ``application`` cuando se requiera orquestar
  varios servicios de dominio.

Principios de diseño
--------------------
* **Idempotencia:** Las funciones que modifican el estado (p. ej.
  ``change_lead_stage``) pueden invocarse varias veces sin efectos secundarios
  inesperados. Si la etapa destino es igual a la actual, simplemente se
  actualiza la marca de último contacto y se registra la actividad.
* **Trazabilidad:** Todo cambio de etapa genera una entrada en
  ``LeadActivity``, incluso los movimientos automáticos disparados por
  ``auto_advance_eligible_leads``.
* **Seguridad de tipos:** Todas las firmas públicas usan *type hints* y
  retornan tipos bien definidos (``bool``, ``Lead``, ``dict``, ``QuerySet``,
  etc.) para facilitar el autocompletado y la detección temprana de errores.

Véase también
-------------
* :doc:`/docs/sdd/sdd_final` – Especificación detallada de las apps
  ``tenants`` y ``crm``.
* :doc:`/docs/blocks/B04` – Documentación del bloque de endpoints CRM.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.cache import cache
from django.db.models import Count, QuerySet
from django.utils import timezone

from crm.domain.models import Lead, LeadActivity
from ingesta.models import ChatUser, DailyTextSummary


def change_lead_stage(
    lead: Lead,
    new_stage: str,
    performed_by: str = "system",
) -> Lead:
    """Actualiza la etapa de un lead y registra la transición como actividad.

    Es el **único punto de entrada autorizado** para mover un lead de etapa.
    Cualquier vista, tarea o serializador que necesite modificar
    ``current_stage`` debe pasar obligatoriamente por esta función para
    garantizar que:

    * Se actualice la marca ``last_contacted_at``.
    * Se genere una entrada de auditoría en ``LeadActivity``.

    Parámetros
    ----------
    lead : Lead
        Instancia del lead que se desea mover. Debe estar previamente
        persistida en base de datos.
    new_stage : str
        Nombre legible de la etapa destino. No se valida contra el pipeline
        del tenant; esa responsabilidad recae en la capa de interfaces o en
        los serializadores.
    performed_by : str, opcional
        Identificador de quien ejecuta la acción. En la API se recomienda usar
        el nombre de usuario o ``"api"``; para transiciones automáticas se
        utiliza el valor por defecto ``"system"``.

    Retorna
    -------
    Lead
        La misma instancia ``lead`` ya persistida con los campos
        ``current_stage``, ``last_contacted_at`` y ``updated_at``
        actualizados.

    Ejemplo
    -------
    >>> lead = Lead.objects.first()
    >>> change_lead_stage(lead, "Cotización Enviada", performed_by="admin")
    >>> lead.current_stage
    'Cotización Enviada'
    >>> lead.activities.filter(activity_type="stage_change").exists()
    True

    Notas
    -----
    * Si ``new_stage`` es idéntico a ``lead.current_stage``, igualmente se
      actualiza ``last_contacted_at`` y se registra la actividad (la función
      es idempotente en ese aspecto).
    * La actualización de ``last_contacted_at`` evita que el lead sea
      considerado "estancado" por ``auto_advance_eligible_leads`` justo
      después de un movimiento manual.
    """
    lead.current_stage = new_stage
    lead.last_contacted_at = timezone.now()
    lead.save(
        update_fields=["current_stage", "last_contacted_at", "updated_at"]
    )
    LeadActivity.objects.create(
        lead=lead,
        activity_type="stage_change",
        description=f"Etapa cambiada a {new_stage}",
        performed_by=performed_by,
    )
    return lead


def auto_advance_eligible_leads(tenant: Any) -> QuerySet[Lead]:
    """Avanza automáticamente los leads estancados de un tenant.

    Evalúa todos los leads **abiertos** (``is_closed=False``) del tenant cuya
    última actividad (medida por ``last_contacted_at``) tenga más de 48 horas.
    Si el pipeline del tenant lo permite, cada lead elegible avanza **una sola
    etapa** hacia adelante, respetando las reglas de salto configuradas.

    La función se apoya en el helper privado ``_next_available_stage`` para
    determinar la etapa destino.

    Parámetros
    ----------
    tenant : Tenant
        Instancia del tenant sobre el que se evalúan los leads. Debe tener una
        relación ``pipeline_config`` válida con el campo ``stages``
        correctamente poblado (lista de diccionarios con al menos las claves
        ``name`` y ``order``).

    Retorna
    -------
    QuerySet[Lead]
        Queryset con los leads que **efectivamente fueron avanzados** durante
        esta ejecución. Si ningún lead cumple los criterios, se retorna un
        ``QuerySet`` vacío.

    Ejemplo
    -------
    >>> from tenants.domain.models import Tenant
    >>> tenant = Tenant.objects.get(slug="codensolar")
    >>> avanzados = auto_advance_eligible_leads(tenant)
    >>> print(f"Se avanzaron {avanzados.count()} leads")

    Notas
    -----
    * Si el tenant **no tiene pipeline configurado** o el campo ``stages``
      está vacío, la función retorna un ``QuerySet`` vacío y no lanza
      excepciones.
    * Los leads que ya están en la **última etapa del pipeline** no se
      modifican.
    * Cada avance genera una ``LeadActivity`` con tipo ``"auto_advance"``
      gracias a que internamente se llama a ``change_lead_stage``.
    * Esta función está diseñada para ser invocada desde una tarea Celery
      periódica (cada 4 horas según la configuración actual del sistema).
    """
    try:
        pipeline_stages: list[dict[str, Any]] = list(
            tenant.pipeline_config.stages
        )
    except Exception:
        return Lead.objects.none()

    if not pipeline_stages:
        return Lead.objects.none()

    ordered_stages = sorted(
        pipeline_stages, key=lambda s: s.get("order", 0)
    )
    threshold = timezone.now() - timedelta(hours=48)
    eligible_leads = Lead.objects.filter(
        tenant=tenant,
        is_closed=False,
        is_deleted=False,
        last_contacted_at__lt=threshold,
    )
    advanced: list[int] = []
    for lead in eligible_leads:
        next_stage = _next_available_stage(lead.current_stage, ordered_stages)
        if next_stage and next_stage != lead.current_stage:
            change_lead_stage(lead, next_stage, performed_by="auto_advance")
            advanced.append(lead.pk)
    return Lead.objects.filter(pk__in=advanced)


def _next_available_stage(
    current_stage: str, ordered_stages: list[dict[str, Any]]
) -> str | None:
    """Retorna la próxima etapa que **no** debe ser saltada.

    Recorre la lista ordenada de etapas a partir de la posición de
    ``current_stage``. Si una etapa tiene la clave ``skip_allowed`` en
    ``True``, se omite y se continúa buscando. Si no queda ninguna etapa
    siguiente, retorna ``None``.

    Parámetros
    ----------
    current_stage : str
        Nombre de la etapa actual del lead.
    ordered_stages : list[dict[str, Any]]
        Lista de etapas del pipeline ordenadas por ``order``. Cada elemento
        debe ser un diccionario con al menos las claves ``name`` y,
        opcionalmente, ``skip_allowed``.

    Retorna
    -------
    str o None
        El nombre de la siguiente etapa válida, o ``None`` si el lead ya está
        en la última etapa o si ``current_stage`` no se encuentra en la lista.

    Ejemplo
    -------
    >>> stages = [
    ...     {"name": "Lead", "order": 1},
    ...     {"name": "Calificación", "order": 2, "skip_allowed": True},
    ...     {"name": "Cotización", "order": 3},
    ... ]
    >>> _next_available_stage("Lead", stages)
    'Cotización'
    """
    try:
        current_idx = next(
            i
            for i, stage in enumerate(ordered_stages)
            if stage.get("name") == current_stage
        )
    except StopIteration:
        return None

    for idx in range(current_idx + 1, len(ordered_stages)):
        stage = ordered_stages[idx]
        if not stage.get("skip_allowed", False):
            return stage.get("name")
    return None


def create_reopen_lead(original_lead: Lead, first_stage: str, performed_by: str = "system") -> Lead:
    """Crea un nuevo lead como reopening (recompra) de uno cerrado.

    El lead original permanece intacto en su etapa cerrada. El nuevo lead
    se crea en la primera etapa del pipeline con los datos del contacto
    y producto del lead original.

    Args:
        original_lead: Lead cerrado del que se parte.
        first_stage: Nombre de la primera etapa del pipeline.
        performed_by: Usuario que ejecuta la acción.

    Returns:
        La nueva instancia de Lead creada.
    """
    new_lead = Lead.objects.create(
        tenant=original_lead.tenant,
        contact=original_lead.contact,
        current_stage=first_stage,
        product_of_interest=original_lead.product_of_interest,
        product_category=original_lead.product_category,
        is_recompra=True,
    )
    LeadActivity.objects.create(
        lead=new_lead,
        activity_type="recompra",
        description=f"Nueva oportunidad generada a partir de lead cerrado {original_lead.id}",
        performed_by=performed_by,
    )
    return new_lead


def get_lead_summary(lead: Lead) -> DailyTextSummary | None:
    """Obtiene el resumen IA más reciente del contacto asociado al lead.

    Busca el ``ChatUser`` cuyo ``phone_number`` coincida con el del contacto
    vinculado al lead. Si lo encuentra, retorna el último
    ``DailyTextSummary`` generado para ese usuario.

    Resultado cacheado por 1 hora (``lead_summary_{lead.id}``).
    La caché se invalida automáticamente mediante señal post_save/post_delete
    de ``DailyTextSummary`` (ver ``crm.signals``).

    Parámetros
    ----------
    lead : Lead
        Lead cuyo contacto se usa como llave de búsqueda.

    Retorna
    -------
    DailyTextSummary o None
        El resumen diario más reciente, o ``None`` si no se encuentra ningún
        ``ChatUser`` con el mismo número de teléfono o si ese usuario no tiene
        resúmenes generados.

    Notas
    -----
    * La búsqueda se hace exclusivamente por ``phone_number`` porque es el
      campo común entre ``Contact`` (app CRM) y ``ChatUser`` (app ingesta).
      Si el número de teléfono está vacío, la función retorna ``None`` de
      inmediato.
    * En el futuro podría añadirse un campo ``chat_user`` en el modelo
      ``Contact`` para hacer la relación directa y evitar esta búsqueda por
      coincidencia de teléfono.

    Ejemplo
    -------
    >>> lead = Lead.objects.first()
    >>> summary = get_lead_summary(lead)
    >>> if summary:
    ...     print(summary.text)
    """
    cache_key = f"lead_summary_{lead.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not lead.contact:
        return None

    phone_number = (lead.contact.phone_number or "").strip()
    if not phone_number:
        return None

    chat_user = ChatUser.objects.filter(phone_number=phone_number).first()
    if chat_user is None:
        return None

    result = (
        DailyTextSummary.objects.filter(user=chat_user)
        .order_by("-summary_date", "-updated_at")
        .first()
    )
    cache.set(cache_key, result, 3600)
    return result


def get_leads_stats(tenant: Any) -> dict[str, Any]:
    """Calcula las métricas agregadas del pipeline para un tenant.

    Retorna un diccionario con los siguientes indicadores clave:

    * ``total_leads`` : Cantidad total de leads del tenant.
    * ``leads_nuevos_hoy`` : Leads creados durante el día actual.
    * ``leads_por_etapa`` : Diccionario ``{etapa: cantidad}`` con la
      distribución de leads abiertos y cerrados por etapa.
    * ``active_leads`` : Cantidad de leads que aún no están cerrados
      (``is_closed=False``).
    * ``won_leads`` : Cantidad de leads cerrados como ganados
      (``is_closed=True, closed_result="won"``).

    Parámetros
    ----------
    tenant : Tenant
        Instancia del tenant sobre el que se realiza la agregación.

    Retorna
    -------
    dict[str, Any]
        Diccionario con las métricas descritas. Las claves son cadenas, los
        valores son enteros o diccionarios anidados.

    Ejemplo
    -------
    >>> from tenants.domain.models import Tenant
    >>> tenant = Tenant.objects.get(slug="codensolar")
    >>> stats = get_leads_stats(tenant)
    >>> print(stats["total_leads"])
    8
    >>> print(stats["leads_por_etapa"])
    {'Lead': 3, 'Cotización Enviada': 2, 'Cerrado Ganado': 1}

    Notas
    -----
    * La función realiza varias consultas a la base de datos, pero cada una es
      ligera gracias a los índices definidos en ``Lead.Meta.indexes``.
    * Si el tenant no tiene leads, todas las métricas retornarán cero o
      diccionarios vacíos.
    """
    leads = Lead.objects.filter(tenant=tenant, is_deleted=False)
    today = timezone.localdate()
    leads_por_etapa = {
        row["current_stage"]: row["total"]
        for row in leads.values("current_stage").annotate(total=Count("id"))
    }
    return {
        "total_leads": leads.count(),
        "leads_nuevos_hoy": leads.filter(created_at__date=today).count(),
        "leads_por_etapa": leads_por_etapa,
        "active_leads": leads.filter(is_closed=False).count(),
        "won_leads": leads.filter(is_closed=True, closed_result="won").count(),
    }