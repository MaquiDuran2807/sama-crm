"""Vistas de la app `crm`.

Este modulo contiene tanto las vistas REST de la API como las vistas HTML que
renderizan el dashboard Kanban y el detalle de lead del CRM. La capa de
interfaces recibe peticiones HTTP y las traduce a operaciones del dominio:
crear/editar contactos, crear/editar leads, registrar cambios de etapa,
obtener resenas IA y calcular metricas del pipeline.
"""

from collections import defaultdict
from datetime import timedelta
from functools import lru_cache
import unicodedata
from pathlib import Path
from typing import Any

from django.db import models
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views import View
from django.utils import timezone

from tenants.domain.models import Tenant
from tenants.domain.services import get_pipeline_stages
from crm.domain.models import Contact, Lead, LeadSource, LeadActivity, Tag, LeadTag, LeadTask
from django.db.models.functions import TruncDate
from crm.domain.services import change_lead_stage, get_leads_stats, get_lead_summary
from crm.domain.contact_sync import sync_contact_from_whatsapp
from crm.interfaces.serializers import (
    ContactSerializer,
    LeadSerializer,
    LeadDetailSerializer,
    LeadCreateSerializer,
    LeadSummarySerializer,
    LeadsStatsSerializer,
    TagSerializer,
    LeadTagSerializer,
    TaskSerializer,
)


@api_view(["POST"])
@permission_classes([AllowAny])
def webhook_sync_contact(request):
    """Webhook para sincronizar un contacto desde WhatsApp/ingesta al CRM.

    Recibe un payload JSON con ``phone_number``, ``tenant_slug`` y
    opcionalmente ``full_name``. Crea o actualiza tanto el ChatUser
    (ingesta) como el Contact (crm) correspondientes.

    POST /api/crm/webhook/chat/
    """
    phone_number = request.data.get("phone_number", "").strip()
    tenant_slug = request.data.get("tenant_slug", "").strip()
    full_name = request.data.get("full_name", "").strip()

    if not phone_number:
        return Response(
            {"detail": "phone_number es obligatorio."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not tenant_slug:
        return Response(
            {"detail": "tenant_slug es obligatorio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
    contact = sync_contact_from_whatsapp(tenant, phone_number, full_name)
    serializer = ContactSerializer(contact)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para contactos asociados a un tenant.

    El `tenant_slug` se espera en la query string porque la API opera sobre un
    tenant concreto por peticion y la seleccion del tenant se resuelve fuera de
    la capa de dominio.
    """
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Construye el queryset restringido al tenant indicado por query param."""

        tenant_slug = self.request.query_params.get("tenant_slug")
        if not tenant_slug:
            return Contact.objects.none()
        return Contact.objects.filter(tenant__slug=tenant_slug, tenant__is_active=True)

    def perform_create(self, serializer):
        """Persiste un contacto asociandolo al tenant resuelto por slug."""

        tenant_slug = self.request.query_params.get("tenant_slug")
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        serializer.save(tenant=tenant)


class LeadViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para leads del tenant activo en la peticion."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Selecciona el serializador apropiado segun la accion de DRF."""

        if self.action == "create":
            return LeadCreateSerializer
        if self.action == "retrieve":
            return LeadDetailSerializer
        return LeadSerializer

    def get_queryset(self):
        """Devuelve los leads activos del tenant filtrando por etapa o contacto."""

        tenant_slug = self.request.query_params.get("tenant_slug")
        if not tenant_slug:
            return Lead.objects.none()

        qs = Lead.objects.filter(tenant__slug=tenant_slug, tenant__is_active=True)

        stage = self.request.query_params.get("stage")
        if stage:
            qs = qs.filter(current_stage=stage)

        contact_id = self.request.query_params.get("contact_id")
        if contact_id:
            qs = qs.filter(contact_id=contact_id)

        has_tasks = self.request.query_params.get("has_tasks")
        if has_tasks == "true":
            qs = qs.filter(tasks__isnull=False).distinct()
        elif has_tasks == "false":
            qs = qs.filter(tasks__isnull=True)

        task_due_before = self.request.query_params.get("task_due_before")
        if task_due_before:
            qs = qs.filter(tasks__due_date__lte=task_due_before, tasks__is_completed=False).distinct()

        task_due_after = self.request.query_params.get("task_due_after")
        if task_due_after:
            qs = qs.filter(tasks__due_date__gte=task_due_after, tasks__is_completed=False).distinct()

        tag_id = self.request.query_params.get("tag")
        if tag_id:
            qs = qs.filter(lead_tags__tag_id=tag_id).distinct()

        return qs.select_related("contact", "tenant")

    def _username(self):
        """Retorna el nombre de usuario actual o 'admin' como fallback."""
        return self.request.user.username or "admin"

    def perform_create(self, serializer):
        """Crea un lead y, si corresponde, su fuente de origen asociada."""
        tenant_slug = self.request.query_params.get("tenant_slug")
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        lead = serializer.save(tenant=tenant)

        utm_source = self.request.data.get("utm_source")
        if utm_source:
            LeadSource.objects.create(
                lead=lead,
                platform=self.request.data.get("platform", "web"),
                utm_source=utm_source,
                utm_medium=self.request.data.get("utm_medium", ""),
                utm_campaign=self.request.data.get("utm_campaign", ""),
                landing_page_url=self.request.data.get("landing_page_url", ""),
            )
        LeadActivity.objects.create(
            lead=lead,
            activity_type="created",
            description="Lead creado",
            performed_by=self._username(),
        )

    def perform_destroy(self, instance):
        """Soft delete del lead: marca como eliminado y registra actividad."""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.deleted_by = self._username()
        instance.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
        LeadActivity.objects.create(
            lead=instance,
            activity_type="deleted",
            description="Lead enviado a papelera",
            performed_by=self._username(),
        )

    def perform_update(self, serializer):
        """Actualiza un lead y registra el cambio de etapa cuando aplique."""
        old_stage = self.get_object().current_stage
        new_stage = serializer.validated_data.get("current_stage", old_stage)
        lead = serializer.save()

        if old_stage != new_stage:
            change_lead_stage(lead, new_stage, performed_by=self._username())

            new_stage_lower = new_stage.lower()
            if "cerrado" in new_stage_lower or "closed" in new_stage_lower:
                lead.is_closed = True
                if "ganado" in new_stage_lower or "won" in new_stage_lower:
                    lead.closed_result = "won"
                elif "perdido" in new_stage_lower or "lost" in new_stage_lower:
                    lead.closed_result = "lost"
                lead.save(update_fields=["is_closed", "closed_result", "updated_at"])

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        """Entrega el ultimo resumen IA disponible para el lead solicitado."""
        lead = self.get_object()
        daily_summary = get_lead_summary(lead)
        if not daily_summary:
            return Response({"detail": "No hay resúmenes disponibles."}, status=404)
        serializer = LeadSummarySerializer(daily_summary)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Devuelve metricas agregadas del pipeline para el tenant indicado."""
        tenant_slug = request.query_params.get("tenant_slug")
        if not tenant_slug:
            return Response({"detail": "tenant_slug es obligatorio."}, status=400)
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        stats = get_leads_stats(tenant)
        serializer = LeadsStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add_note")
    def add_note(self, request, pk=None):
        """Registra una nota como actividad en el lead.

        POST /api/crm/leads/{id}/add_note/
        Body: {"note": "texto de la nota"}
        A diferencia de add_activity, permite nota vacía (para registro de movimiento).
        """
        lead = self.get_object()
        note = request.data.get("note", "").strip()
        performed_by = self._username()
        if note:
            LeadActivity.objects.create(
                lead=lead,
                activity_type="note_added",
                description=note,
                performed_by=performed_by,
            )
        return Response(
            {"detail": "Nota guardada."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="add_activity")
    def add_activity(self, request, pk=None):
        """Registra una actividad manual en el lead.

        POST /api/crm/leads/{id}/add_activity/
        Body: {"description": "descripción de la actividad"}
        """
        lead = self.get_object()
        description = request.data.get("description", "").strip()
        if not description:
            return Response(
                {"detail": "El campo 'description' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        LeadActivity.objects.create(
            lead=lead,
            activity_type="manual",
            description=description,
            performed_by=self._username(),
        )
        return Response(
            {"detail": "Actividad registrada correctamente."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """Restaura un lead previamente eliminado (soft delete).

        POST /api/crm/leads/{id}/restore/?tenant_slug=...
        """
        tenant_slug = request.query_params.get("tenant_slug")
        if not tenant_slug:
            return Response({"detail": "tenant_slug es obligatorio."}, status=400)
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        lead = get_object_or_404(
            Lead.all_objects.filter(tenant=tenant),
            pk=pk,
        )
        if not lead.is_deleted:
            return Response(
                {"detail": "El lead no está eliminado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        lead.is_deleted = False
        lead.deleted_at = None
        lead.deleted_by = ""
        lead.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
        LeadActivity.objects.create(
            lead=lead,
            activity_type="restored",
            description="Lead restaurado de la papelera",
            performed_by=self._username(),
        )
        return Response({"detail": "Lead restaurado correctamente."})

    @action(detail=False, methods=["get"], url_path="trash")
    def trash(self, request):
        """Lista los leads eliminados de un tenant.

        GET /api/crm/leads/trash/?tenant_slug=...
        """
        tenant_slug = request.query_params.get("tenant_slug")
        if not tenant_slug:
            return Response({"detail": "tenant_slug es obligatorio."}, status=400)
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        deleted_leads = (
            Lead.all_objects.filter(tenant=tenant, is_deleted=True)
            .select_related("contact", "tenant")
        )
        serializer = LeadSerializer(deleted_leads, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="reopen")
    def reopen(self, request, pk=None):
        """Crea un nuevo lead a partir de uno cerrado (recompra).

        POST /api/crm/leads/{id}/reopen/?tenant_slug=...
        El lead original permanece cerrado. Se crea un nuevo lead en la
        primera etapa del pipeline para el mismo contacto.
        """
        lead = self.get_object()
        if not lead.is_closed:
            return Response(
                {"detail": "El lead no está cerrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from tenants.domain.services import get_pipeline_stages
        stages = get_pipeline_stages(lead.tenant)
        if not stages:
            return Response(
                {"detail": "No hay etapas configuradas en el pipeline."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sorted_stages = sorted(stages, key=lambda s: s.get("order", 0))
        first_stage = sorted_stages[0].get("name", "")

        from crm.domain.services import create_reopen_lead
        new_lead = create_reopen_lead(lead, first_stage, performed_by=self._username())
        serializer = LeadDetailSerializer(new_lead)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="tasks")
    def tasks(self, request, pk=None):
        """Lista o crea tareas para el lead.

        GET /api/crm/leads/{id}/tasks/
        POST /api/crm/leads/{id}/tasks/ — body: {description, due_date}
        """
        lead = self.get_object()
        if request.method == "GET":
            tasks_qs = lead.tasks.all().order_by("due_date", "-created_at")
            tasks_list = list(tasks_qs)
            tasks_with_null = [t for t in tasks_list if t.due_date is None]
            tasks_without_null = [t for t in tasks_list if t.due_date is not None]
            tasks_without_null.sort(key=lambda x: (x.due_date is None, x.due_date, -x.created_at.timestamp()))
            tasks_sorted = tasks_without_null + tasks_with_null
            serializer = TaskSerializer(tasks_sorted, many=True)
            return Response(serializer.data)
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(lead=lead)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch", "delete"], url_path="tasks/(?P<task_id>[0-9]+)")
    def task_detail(self, request, pk=None, task_id=None):
        """Actualiza o elimina una tarea del lead.

        PATCH /api/crm/leads/{id}/tasks/{task_id}/ — body: {description, due_date, is_completed}
        DELETE /api/crm/leads/{id}/tasks/{task_id}/
        """
        lead = self.get_object()
        task = get_object_or_404(lead.tasks, pk=task_id)
        if request.method == "PATCH":
            data = request.data.copy()
            new_is_completed = data.get("is_completed")
            if new_is_completed is not None:
                new_is_completed = new_is_completed in [True, "true", "True", "1", 1]
                current_is_completed = task.is_completed
                if new_is_completed and not current_is_completed:
                    task.completed_at = timezone.now()
                    task.is_completed = True
                    task.save(update_fields=["is_completed", "completed_at"])
                    serializer = TaskSerializer(task)
                    return Response(serializer.data)
                elif not new_is_completed and current_is_completed:
                    task.completed_at = None
                    task.is_completed = False
                    task.save(update_fields=["is_completed", "completed_at"])
                    serializer = TaskSerializer(task)
                    return Response(serializer.data)
            serializer = TaskSerializer(task, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="add_tag")
    def add_tag(self, request, pk=None):
        """Añade una etiqueta al lead.

        POST /api/crm/leads/{id}/add_tag/
        Body: {tag_id: int}
        """
        lead = self.get_object()
        tag_id = request.data.get("tag_id")
        if not tag_id:
            return Response({"detail": "tag_id es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        tag = get_object_or_404(Tag, pk=tag_id, tenant=lead.tenant)
        lead_tag, created = LeadTag.objects.get_or_create(lead=lead, tag=tag)
        serializer = LeadTagSerializer(lead_tag)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="remove_tag")
    def remove_tag(self, request, pk=None):
        """Quita una etiqueta del lead.

        POST /api/crm/leads/{id}/remove_tag/
        Body: {tag_id: int}
        """
        lead = self.get_object()
        tag_id = request.data.get("tag_id")
        if not tag_id:
            return Response({"detail": "tag_id es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = lead.lead_tags.filter(tag_id=tag_id).delete()
        if deleted:
            return Response({"detail": "Etiqueta eliminada."})
        return Response({"detail": "Etiqueta no encontrada."}, status=status.HTTP_404_NOT_FOUND)


def _format_time_since(updated_at):
    """Formatea el tiempo transcurrido desde la ultima actualizacion.

    Args:
        updated_at: Marca temporal del ultimo cambio registrado en el lead.

    Returns:
        Cadena legible para mostrar en la tarjeta del dashboard.
    """

    delta = timezone.now() - updated_at
    if delta.days > 0:
        return f"hace {delta.days} d"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"hace {hours}h"
    minutes = max(delta.seconds // 60, 1)
    return f"hace {minutes}m"


def _humanize_duration(seconds: float) -> str:
    """Convierte segundos a un formato legible (2h 15m, 3d, etc.)."""
    if seconds < 60:
        return "< 1 min"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    minutes = minutes % 60
    if hours < 24:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    days = hours // 24
    hours = hours % 24
    if days < 30:
        return f"{days}d {hours}h" if hours else f"{days}d"
    months = days // 30
    days = days % 30
    return f"{months}m {days}d" if days else f"{months}m"


class CrmDashboardTemplateView(LoginRequiredMixin, View):
    """Vista HTML del dashboard Kanban del CRM.

    Args de la ruta:
        tenant_slug: Slug publico del tenant que define el contexto comercial
            a visualizar en el tablero.
    """

    template_name = "crm/dashboard.html"
    login_url = "/admin/login/"

    def get(self, request, tenant_slug: str, *args, **kwargs):
        """Construye el contexto del tablero Kanban para un tenant concreto."""

        tenant = get_object_or_404(
            Tenant.objects.select_related("pipeline_config"),
            slug=tenant_slug,
            is_active=True,
        )
        stats = get_leads_stats(tenant)
        stages = get_pipeline_stages(tenant)
        leads = (
            Lead.objects.filter(tenant=tenant, is_deleted=False)
            .select_related("contact")
            .prefetch_related("lead_tags__tag")
            .order_by("current_stage", "-updated_at")
        )

        leads_by_stage = defaultdict(list)
        for lead in leads:
            lead.time_since_update = _format_time_since(lead.updated_at)
            lead.is_new = lead.created_at.date() == timezone.localdate()
            lead.tags_list = [
                {"id": lt.tag.id, "name": lt.tag.name, "color": lt.tag.color}
                for lt in lead.lead_tags.all()
            ]
            lead.tags_ids = [str(lt.tag.id) for lt in lead.lead_tags.all()]
            leads_by_stage[lead.current_stage].append(lead)

        pipeline = []
        for stage in stages:
            stage_name = stage.get("name", "")
            stage_leads = leads_by_stage.get(stage_name, [])
            stage_lower = stage_name.lower()
            is_closed = "cerrado" in stage_lower or "closed" in stage_lower
            pipeline.append(
                {
                    "name": stage_name,
                    "color": stage.get("color", "#64748b"),
                    "order": stage.get("order", 0),
                    "lead_count": len(stage_leads),
                    "leads": stage_leads,
                    "is_closed": is_closed,
                }
            )

        context = {
            "tenant": tenant,
            "stats": stats,
            "pipeline": pipeline,
        }
        return render(request, self.template_name, context)


class CrmLeadDetailTemplateView(LoginRequiredMixin, View):
    """Vista HTML de detalle para un lead concreto del CRM.

    Args de la ruta:
        tenant_slug: Slug del tenant dueño del lead.
        lead_id: Identificador numérico del lead a renderizar.
    """

    template_name = "crm/lead_detail.html"
    login_url = "/admin/login/"

    def get(self, request, tenant_slug: str, lead_id: int, *args, **kwargs):
        """Construye el contexto del detalle del lead y su actividad asociada."""

        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        lead = get_object_or_404(
            Lead.objects.select_related("contact", "tenant", "source").prefetch_related("activities", "lead_tags__tag"),
            pk=lead_id,
            tenant=tenant,
        )
        lead.tags_list = [
            {"id": lt.tag.id, "name": lt.tag.name, "color": lt.tag.color}
            for lt in lead.lead_tags.all()
        ]
        summary = get_lead_summary(lead)
        pipeline_stages = get_pipeline_stages(tenant)
        activities = lead.activities.all()
        now = timezone.now()

        # Añadir time_since a cada actividad para mostrar tiempo relativo
        for activity in activities:
            activity.time_since = _format_time_since(activity.created_at)

        # ── Calcular trace_data con duraciones de etapa ──
        stage_changes = [
            a for a in activities if a.activity_type == "stage_change"
        ]
        stage_changes.sort(key=lambda a: a.created_at)

        # entries: lista de (stage_name, entry_datetime, exit_datetime)
        entries: list[tuple[str, Any, Any]] = []

        if stage_changes:
            # Etapa inicial (antes del primer cambio)
            first_target = stage_changes[0].description.replace(
                "Etapa cambiada a ", ""
            ).strip()
            prev_stage = None
            for i, s in enumerate(pipeline_stages):
                if s.get("name") == first_target and i > 0:
                    prev_stage = pipeline_stages[i - 1].get("name")
                    break
            if prev_stage:
                entries.append((prev_stage, lead.created_at, stage_changes[0].created_at))

            # Etapas registradas por cada stage_change
            for i, act in enumerate(stage_changes):
                stage_name = act.description.replace("Etapa cambiada a ", "").strip()
                entry_time = act.created_at
                exit_time = (
                    stage_changes[i + 1].created_at
                    if i + 1 < len(stage_changes)
                    else now
                )
                entries.append((stage_name, entry_time, exit_time))
        else:
            # Nunca cambió de etapa; única etapa desde creación
            entries.append((lead.current_stage, lead.created_at, now))

        trace_data = []
        for stage in pipeline_stages:
            name = stage.get("name", "")
            is_current = name == lead.current_stage
            duration_str = ""
            for sname, entry, exit_ in entries:
                if sname == name:
                    duration_seconds = (exit_ - entry).total_seconds()
                    duration_str = _humanize_duration(duration_seconds)
                    break
            trace_data.append({
                "name": name,
                "color": stage.get("color", "#64748b"),
                "duration": duration_str,
                "is_current": is_current,
                "order": stage.get("order", 0),
            })

        # Notas: actividades de tipo note_added (más recientes primero)
        notes = [a for a in activities if a.activity_type == "note_added"]

        context = {
            "tenant": tenant,
            "lead": lead,
            "summary": summary,
            "pipeline_stages": pipeline_stages,
            "trace_data": trace_data,
            "activities": activities,
            "notes": notes[:5],
        }
        return render(request, self.template_name, context)


class CrmTrashTemplateView(LoginRequiredMixin, View):
    """Vista HTML de la papelera de leads eliminados.

    Args de la ruta:
        tenant_slug: Slug del tenant.
    """

    template_name = "crm/trash.html"
    login_url = "/admin/login/"

    def get(self, request, tenant_slug: str, *args, **kwargs):
        """Lista los leads eliminados del tenant."""

        tenant = get_object_or_404(
            Tenant.objects.select_related("pipeline_config"),
            slug=tenant_slug,
            is_active=True,
        )
        deleted_leads = (
            Lead.all_objects.filter(tenant=tenant, is_deleted=True)
            .select_related("contact")
            .order_by("-deleted_at")
        )
        for lead in deleted_leads:
            lead.time_since_update = _format_time_since(lead.updated_at)

        context = {
            "tenant": tenant,
            "deleted_leads": deleted_leads,
        }
        return render(request, self.template_name, context)


def _get_csrf_token(request) -> str:
    """Obtiene el CSRF token del request."""
    try:
        from django.middleware.csrf import get_token
        return get_token(request)
    except Exception:
        return ""


class CrmTrashTemplateView(LoginRequiredMixin, View):
    """Vista HTML de la papelera de leads eliminados.

    Args de la ruta:
        tenant_slug: Slug del tenant.
    """

    template_name = "crm/trash.html"
    login_url = "/admin/login/"

    def get(self, request, tenant_slug: str, *args, **kwargs):
        """Lista los leads eliminados del tenant."""
        csrf_token = _get_csrf_token(request)
        tenant = get_object_or_404(
            Tenant.objects.select_related("pipeline_config"),
            slug=tenant_slug,
            is_active=True,
        )
        deleted_leads = (
            Lead.all_objects.filter(tenant=tenant, is_deleted=True)
            .select_related("contact")
            .order_by("-deleted_at")
        )
        for lead in deleted_leads:
            lead.time_since_update = _format_time_since(lead.updated_at)

        context = {
            "tenant": tenant,
            "deleted_leads": deleted_leads,
            "csrf_token": csrf_token,
        }
        return render(request, self.template_name, context)


class CrmAnalyticsTemplateView(LoginRequiredMixin, View):
    """Vista HTML del dashboard de analíticas del CRM."""

    template_name = "crm/analytics.html"
    login_url = "/admin/login/"

    def get(self, request, tenant_slug: str, *args, **kwargs):
        """Renderiza el dashboard de analíticas con datos iniciales."""
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        csrf_token = _get_csrf_token(request)
        context = {
            "tenant": tenant,
            "csrf_token": csrf_token,
        }
        return render(request, self.template_name, context)


class PipelineConfigView(LoginRequiredMixin, View):
    """Vista HTML para configurar el pipeline de ventas del tenant."""

    template_name = "crm/pipeline_config.html"
    login_url = "/admin/login/"

    def get(self, request, tenant_slug: str, *args, **kwargs):
        """Renderiza la página de configuración del pipeline."""
        from tenants.domain.models import PipelineConfig

        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        pipeline_config = get_object_or_404(PipelineConfig, tenant=tenant)
        csrf_token = _get_csrf_token(request)
        context = {
            "tenant": tenant,
            "stages": pipeline_config.stages,
            "csrf_token": csrf_token,
        }
        return render(request, self.template_name, context)


@lru_cache(maxsize=1)
def _normalize_city_key(name: str) -> str:
    """Normaliza un nombre de ciudad para busqueda en el diccionario de coordenadas."""
    normalized = unicodedata.normalize("NFD", name)
    normalized = normalized.translate({c: "" for c in range(0x0300, 0x0370)})
    return normalized.lower()


def load_city_coordinates() -> dict[str, dict[str, float]]:
    """Carga coordenadas de ciudades desde el CSV estatico.

    Returns:
        Dict mapping normalized city names to {latitud, longitud}.
    """
    import csv

    cities_path = Path(__file__).resolve().parent.parent / "static" / "crm" / "data" / "ciudades_colombia.csv"
    coords: dict[str, dict[str, float]] = {}

    try:
        with cities_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw = row.get("nombre", "").strip()
                if raw:
                    key = _normalize_city_key(raw)
                    coords[key] = {
                        "latitud": float(row["latitud"]),
                        "longitud": float(row["longitud"]),
                    }
    except FileNotFoundError:
        pass

    return coords


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_api(request, tenant_slug: str):
    """API de analíticas del pipeline.

    Query params:
        days: int (default 30) — filtra leads creados en los últimos N días.
        source: str (opcional) — filtra por LeadSource.platform.

    Returns JSON con funnel, leads_by_source, leads_by_day y summary.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

    days = int(request.query_params.get("days", 30))
    offset = int(request.query_params.get("offset", 0))
    source_filter = request.query_params.get("source", "").strip()

    since = timezone.now() - timedelta(days=days + (offset * days))
    until = timezone.now() - timedelta(days=(offset * days)) if offset > 0 else None

    leads_qs = Lead.objects.filter(
        tenant=tenant,
        is_deleted=False,
        created_at__gte=since,
    )
    if until:
        leads_qs = leads_qs.filter(created_at__lte=until)

    if source_filter:
        leads_qs = leads_qs.filter(source__platform=source_filter)

    # ── Funnel: leads por etapa, ordenados por pipeline ──
    try:
        pipeline_stages = list(tenant.pipeline_config.stages or [])
    except Exception:
        pipeline_stages = []

    stage_counts = (
        leads_qs.values("current_stage")
        .annotate(count=Count("id"))
    )
    stage_map = {row["current_stage"]: row["count"] for row in stage_counts}

    funnel = []
    for stage in sorted(pipeline_stages, key=lambda s: s.get("order", 0)):
        funnel.append({
            "stage": stage.get("name", ""),
            "count": stage_map.get(stage.get("name", ""), 0),
        })
    for stage_name in leads_qs.values_list("current_stage", flat=True).distinct():
        if not any(s.get("name") == stage_name for s in pipeline_stages):
            funnel.append({"stage": stage_name, "count": stage_map.get(stage_name, 0)})

    # ── Leads by source ──
    source_counts = (
        leads_qs.filter(source__isnull=False)
        .values("source__platform")
        .annotate(count=Count("id"))
    )
    leads_by_source = [
        {"source": row["source__platform"] or "unknown", "count": row["count"]}
        for row in source_counts
    ]

    # ── Leads by day (filtered by source if selected) ──
    date_counts = (
        leads_qs.extra(select={"day": "DATE(crm_lead.created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    leads_by_day = [
        {"date": row["day"].strftime("%Y-%m-%d") if hasattr(row["day"], "strftime") else str(row["day"]), "count": row["count"]}
        for row in date_counts
    ]

    # ── Total leads by day (always ALL sources, ignores source filter) ──
    total_date_counts = (
        Lead.objects.filter(
            tenant=tenant,
            is_deleted=False,
            created_at__gte=since,
        )
        .filter(created_at__lte=timezone.now() - timedelta(days=(offset * days)))
        if offset > 0
        else
        Lead.objects.filter(
            tenant=tenant,
            is_deleted=False,
            created_at__gte=since,
        )
    )
    if until:
        total_date_counts = total_date_counts.filter(created_at__lte=until)
    total_date_counts = (
        total_date_counts.extra(select={"day": "DATE(crm_lead.created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    total_leads_by_day = [
        {"date": row["day"].strftime("%Y-%m-%d") if hasattr(row["day"], "strftime") else str(row["day"]), "count": row["count"]}
        for row in total_date_counts
    ]

    # ── Summary ──
    total_leads = leads_qs.count()
    won_leads = leads_qs.filter(is_closed=True, closed_result="won").count()
    conversion_rate = (won_leads / total_leads) if total_leads > 0 else 0

    week_start = timezone.now() - timedelta(days=7)
    leads_this_week = leads_qs.filter(created_at__gte=week_start).count()

    closed_won = leads_qs.filter(is_closed=True, closed_result="won")
    if closed_won.exists():
        durations = [
            (lead.updated_at - lead.created_at).total_seconds() / 86400
            for lead in closed_won.only("created_at", "updated_at")
            if lead.created_at and lead.updated_at
        ]
        avg_days = sum(durations) / len(durations) if durations else 0
    else:
        avg_days = 0

    # ── Leads by day for closed won ──
    won_qs = Lead.objects.filter(
        tenant=tenant,
        is_deleted=False,
        is_closed=True,
        closed_result="won",
        created_at__gte=since,
    )
    if source_filter:
        won_qs = won_qs.filter(source__platform=source_filter)
    won_date_counts = (
        won_qs.extra(select={"day": "DATE(crm_lead.created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    leads_by_stage_won = [
        {"date": row["day"].strftime("%Y-%m-%d") if hasattr(row["day"], "strftime") else str(row["day"]), "count": row["count"]}
        for row in won_date_counts
    ]

    # ── Leads by day for closed lost ──
    lost_qs = Lead.objects.filter(
        tenant=tenant,
        is_deleted=False,
        is_closed=True,
        closed_result="lost",
        created_at__gte=since,
    )
    if source_filter:
        lost_qs = lost_qs.filter(source__platform=source_filter)
    lost_date_counts = (
        lost_qs.extra(select={"day": "DATE(crm_lead.created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    leads_by_stage_lost = [
        {"date": row["day"].strftime("%Y-%m-%d") if hasattr(row["day"], "strftime") else str(row["day"]), "count": row["count"]}
        for row in lost_date_counts
    ]

    # ── Quotes sent (leads in Cotización Enviada stage) ──
    quotes_qs = Lead.objects.filter(
        tenant=tenant,
        is_deleted=False,
        current_stage__icontains="Cotizacion",
        created_at__gte=since,
    )
    if source_filter:
        quotes_qs = quotes_qs.filter(source__platform=source_filter)
    quotes_date_counts = (
        quotes_qs.extra(select={"day": "DATE(crm_lead.created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    quotes_sent = [
        {"date": row["day"].strftime("%Y-%m-%d") if hasattr(row["day"], "strftime") else str(row["day"]), "count": row["count"]}
        for row in quotes_date_counts
    ]

    # ── Leads by region (city as department) ──
    region_counts = (
        leads_qs.filter(contact__isnull=False, contact__city__isnull=False)
        .values("contact__city__department__name")
        .annotate(total=Count("id"))
    )
    region_won_counts = dict(
        leads_qs.filter(is_closed=True, closed_result="won", contact__isnull=False, contact__city__isnull=False)
        .values("contact__city__department__name")
        .annotate(won=Count("id"))
        .values_list("contact__city__department__name", "won")
    )
    leads_by_region = []
    for row in region_counts:
        department = row["contact__city__department__name"] or "Sin especificar"
        won = region_won_counts.get(department, 0)
        total = row["total"]
        leads_by_region.append({
            "department": department,
            "total": total,
            "won": won,
            "conversion_rate": round((won / total) * 100, 1) if total > 0 else 0,
        })
    leads_by_region.sort(key=lambda x: x["total"], reverse=True)

    # ── Leads geocoded for heatmap (grouped by department) ──
    import csv
    import os

    static_dir = os.path.join(os.path.dirname(__file__), "..", "static", "crm", "data")

    dept_coords = {}
    with open(os.path.join(static_dir, "departamentos_colombia.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dept_coords[row["nombre"].strip()] = (float(row["latitud"]), float(row["longitud"]))

    dept_counts = defaultdict(int)
    dept_won = defaultdict(int)
    dept_lost = defaultdict(int)

    for lead in (
        leads_qs.filter(contact__isnull=False, contact__city__isnull=False)
        .select_related("contact__city__department")
    ):
        city_obj = lead.contact.city
        if city_obj and city_obj.department and city_obj.department.name in dept_coords:
            dept = city_obj.department.name
            dept_counts[dept] += 1
            if lead.is_closed:
                if lead.closed_result == "won":
                    dept_won[dept] += 1
                elif lead.closed_result == "lost":
                    dept_lost[dept] += 1

    max_total = max(dept_counts.values()) if dept_counts else 1
    max_won = max(dept_won.values()) if dept_won else 1

    leads_geocoded = [
        {
            "latitud": lat,
            "longitud": lng,
            "departamento": dept,
            "total": dept_counts[dept],
            "won": dept_won.get(dept, 0),
            "lost": dept_lost.get(dept, 0),
            "intensidad": round(min(1.0, (dept_counts[dept] / max_total) ** 0.7), 2),
            "intensidad_won": round(min(1.0, (dept_won.get(dept, 0) / max_won) ** 0.7), 2),
        }
        for dept, (lat, lng) in dept_coords.items()
        if dept_counts.get(dept, 0) > 0
    ]

    leads_geocoded.sort(key=lambda x: x["total"], reverse=True)

# ── Leads by source monthly ──
    monthly_platforms = ["meta", "google", "tiktok", "web", "referral"]
    monthly_data = defaultdict(lambda: {p: 0 for p in monthly_platforms})

    source_monthly_counts = (
        leads_qs.filter(source__isnull=False, source__platform__isnull=False)
        .annotate(month=TruncMonth("created_at"))
        .values("month", "source__platform")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    for row in source_monthly_counts:
        month_key = row["month"].strftime("%Y-%m")
        platform = row["source__platform"] or "unknown"
        if platform in monthly_data[month_key]:
            monthly_data[month_key][platform] = row["count"]

    leads_by_source_monthly = [
        {"month": month, **monthly_data[month]}
        for month in sorted(monthly_data.keys())
    ]

    # ── Stage counts by date (all phases) ──
    stage_date_counts = (
        leads_qs.extra(select={"day": "DATE(crm_lead.created_at)"})
        .values("day", "current_stage")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    stage_by_date = defaultdict(lambda: defaultdict(int))
    for row in stage_date_counts:
        day = row["day"].strftime("%Y-%m-%d") if hasattr(row["day"], "strftime") else str(row["day"])
        stage = row["current_stage"] or "unknown"
        stage_by_date[day][stage] = row["count"]

    leads_by_stage = {
        stage["name"]: [
            {"date": day, "count": stage_by_date[day].get(stage["name"], 0)}
            for day in sorted(stage_by_date.keys())
        ]
        for stage in pipeline_stages
    }

    return Response({
        "funnel": funnel,
        "leads_by_source": leads_by_source,
        "leads_by_day": leads_by_day,
        "total_leads_by_day": total_leads_by_day,
        "leads_by_stage_won": leads_by_stage_won,
        "leads_by_stage_lost": leads_by_stage_lost,
        "quotes_sent": quotes_sent,
        "leads_by_region": leads_by_region,
        "leads_geocoded": leads_geocoded,
        "leads_by_source_monthly": leads_by_source_monthly,
        "leads_by_stage": leads_by_stage,
        "pipeline_stages": pipeline_stages,
        "summary": {
            "total_leads": total_leads,
            "won_leads": won_leads,
            "lost_leads": leads_qs.filter(is_closed=True, closed_result="lost").count(),
            "quotes_sent_count": quotes_qs.count(),
            "conversion_rate": round(conversion_rate, 3),
            "avg_days_to_close": round(avg_days, 1),
            "leads_this_week": leads_this_week,
        },
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def tags_list_create(request, tenant_slug):
    """Lista y crea etiquetas para un tenant.

    GET /api/crm/tenants/{slug}/tags/ — lista todas las etiquetas (predefinidas + custom)
    POST /api/crm/tenants/{slug}/tags/ — crea una etiqueta custom
    Body POST: {name: str, color: str (optional)}
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

    if request.method == "GET":
        tags = Tag.objects.filter(tenant=tenant).order_by("name")
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    tag_name = request.data.get("name", "").strip()
    if Tag.objects.filter(tenant=tenant, name__iexact=tag_name).exists():
        return Response(
            {"name": ["Ya existe una etiqueta con este nombre para este tenant."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = TagSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(tenant=tenant, is_predefined=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def tag_delete(request, tenant_slug, tag_id):
    """Elimina una etiqueta no predefinida.

    DELETE /api/crm/tenants/{slug}/tags/{id}/
    Solo elimina si is_predefined=False.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
    tag = get_object_or_404(Tag, pk=tag_id, tenant=tenant)
    if tag.is_predefined:
        return Response(
            {"detail": "No se pueden eliminar etiquetas predefinidas."},
            status=status.HTTP_403_FORBIDDEN,
        )
    tag.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)