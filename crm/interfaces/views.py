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
import hashlib
import hmac
import unicodedata
from pathlib import Path
from typing import Any

from django.db import models
from django.db.models import Avg, Case, Count, IntegerField, Prefetch, Q, Sum, Value, When
from django.db.models.functions import TruncDate, TruncMonth
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, inline_serializer
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views import View
from django.utils import timezone


from tenants.domain.models import Tenant
from crm.interfaces.permissions import TenantAccessMixin, require_tenant_access
from tenants.domain.services import get_pipeline_stages
from crm.domain.models import Contact, Lead, LeadSource, LeadActivity, Tag, LeadTag, LeadTask, KpiTarget, KpiMetricType, Product, LeadProduct
from django.db.models.functions import TruncDate
from crm.domain.services import change_lead_stage, get_leads_stats, get_lead_summary
from crm.domain.contact_sync import sync_contact_from_whatsapp
from crm.application.use_cases import (
    CreateLeadUseCase,
    ChangeLeadStageUseCase,
    AddNoteUseCase,
    ReopenLeadUseCase,
    DeleteLeadUseCase,
    AddActivityUseCase,
    RestoreLeadUseCase,
)
from crm.interfaces.serializers import (
    ContactSerializer,
    LeadSerializer,
    LeadDetailSerializer,
    LeadCreateSerializer,
    LeadSourceSerializer,
    LeadSummarySerializer,
    LeadsStatsSerializer,
    TagSerializer,
    LeadTagSerializer,
    TaskSerializer,
    KpiTargetSerializer,
    KpiTargetCreateSerializer,
    ProductSerializer,
    ProductCreateSerializer,
    LeadProductSerializer,
    LeadProductCreateSerializer,
)


@extend_schema(
    summary="Webhook sincronización WhatsApp",
    description="Sincroniza un contacto desde WhatsApp/ingesta al CRM vía HMAC-SHA256.",
    request=inline_serializer("WebhookSync", fields={
        "phone_number": serializers.CharField(),
        "tenant_slug": serializers.CharField(),
        "full_name": serializers.CharField(required=False),
    }),
    responses={200: OpenApiResponse(description="Contacto sincronizado"), 403: OpenApiResponse(description="Firma inválida")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def webhook_sync_contact(request):
    """Webhook para sincronizar un contacto desde WhatsApp/ingesta al CRM.

    Recibe un payload JSON con ``phone_number``, ``tenant_slug`` y
    opcionalmente ``full_name``. Crea o actualiza tanto el ChatUser
    (ingesta) como el Contact (crm) correspondientes.

    La autenticacion se realiza mediante firma HMAC-SHA256.
    El cliente debe firmar el body JSON con el ``WEBHOOK_SECRET``
    compartido y enviarlo en el header ``X-Webhook-Signature``.

    Ejemplo de generacion de firma (Python)::

        import hmac, hashlib
        secret = settings.WEBHOOK_SECRET
        body = request.body  # raw bytes
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers = {"X-Webhook-Signature": sig}

    POST /api/crm/webhook/chat/
    """
    from django.conf import settings as django_settings

    expected_secret = getattr(django_settings, "WEBHOOK_SECRET", "")
    if not expected_secret or expected_secret == "change-me-in-env":
        return Response(
            {"detail": "Webhook secret no configurado."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    signature = request.headers.get("X-Webhook-Signature", "")
    if not signature:
        return Response(
            {"detail": "Header X-Webhook-Signature es obligatorio."},
            status=status.HTTP_403_FORBIDDEN,
        )

    raw_body = request.body
    expected_sig = hmac.new(
        expected_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return Response(
            {"detail": "Firma HMAC invalida."},
            status=status.HTTP_403_FORBIDDEN,
        )

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


@extend_schema_view(
    list=extend_schema(
        summary="Listar contactos",
        description="Devuelve todos los contactos del tenant activo.",
        parameters=[OpenApiParameter(name="tenant_slug", description="Slug del tenant", required=True, type=str)],
    ),
    retrieve=extend_schema(
        summary="Obtener contacto",
        description="Devuelve el detalle de un contacto por ID.",
    ),
    create=extend_schema(
        summary="Crear contacto",
        description="Crea un nuevo contacto en el tenant activo.",
        request=ContactSerializer,
    ),
    update=extend_schema(summary="Actualizar contacto"),
    partial_update=extend_schema(summary="Actualizar parcialmente contacto"),
    destroy=extend_schema(summary="Eliminar contacto"),
)
class ContactViewSet(TenantAccessMixin, viewsets.ModelViewSet):
    """ViewSet CRUD para contactos asociados a un tenant.

    El `tenant_slug` se espera en la query string porque la API opera sobre un
    tenant concreto por peticion y la seleccion del tenant se resuelve fuera de
    la capa de dominio.
    """
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Construye el queryset restringido al tenant indicado por query param."""
        tenant = self.get_tenant_from_request()
        return Contact.objects.filter(tenant=tenant).select_related(
            "tenant", "referrer_contact"
        ).prefetch_related(
            Prefetch("leads", queryset=Lead.objects.order_by("-created_at"))
        )

    def perform_create(self, serializer):
        """Persiste un contacto asociandolo al tenant resuelto por slug."""
        tenant = self.get_tenant_from_request()
        serializer.save(tenant=tenant)


@extend_schema_view(
    list=extend_schema(
        summary="Listar leads",
        description="Devuelve los leads activos del tenant, con filtros por stage, contacto, tags y tareas.",
        parameters=[
            OpenApiParameter(name="tenant_slug", description="Slug del tenant", required=True, type=str),
            OpenApiParameter(name="stage", description="Filtrar por etapa del pipeline", type=str),
            OpenApiParameter(name="contact_id", description="Filtrar por contacto", type=int),
            OpenApiParameter(name="tag", description="Filtrar por ID de etiqueta", type=int),
            OpenApiParameter(name="has_tasks", description='Filtrar leads con/sin tareas ("true"/"false")', type=str),
        ],
    ),
    retrieve=extend_schema(summary="Obtener lead", description="Devuelve el detalle completo de un lead."),
    create=extend_schema(summary="Crear lead", request=LeadCreateSerializer),
    update=extend_schema(summary="Actualizar lead"),
    partial_update=extend_schema(summary="Actualizar parcialmente lead"),
    destroy=extend_schema(summary="Eliminar lead (soft delete)"),
)
class LeadViewSet(TenantAccessMixin, viewsets.ModelViewSet):
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

        tenant = self.get_tenant_from_request()

        qs = Lead.objects.filter(tenant=tenant, is_deleted=False)
        qs = qs.select_related("contact", "tenant").prefetch_related(
            Prefetch("tasks", queryset=LeadTask.objects.filter(is_completed=False)),
            "lead_tags__tag",
        )

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

        return qs

    def _username(self):
        """Retorna el nombre de usuario actual o 'admin' como fallback."""
        return self.request.user.username or "admin"

    def perform_create(self, serializer):
        """Crea un lead y, si corresponde, su fuente de origen asociada."""
        tenant = self.get_tenant_from_request()
        
        # Obtener los datos del lead y de la UTM
        lead_data = serializer.validated_data
        utm_payload = {
            "platform": self.request.data.get("platform", "web"),
            "utm_source": self.request.data.get("utm_source", ""),
            "utm_medium": self.request.data.get("utm_medium", ""),
            "utm_campaign": self.request.data.get("utm_campaign", ""),
            "landing_page_url": self.request.data.get("landing_page_url", ""),
            "referrer_contact": self.request.data.get("referrer_contact", None),
        }
        
        # Validar UTM antes con el serializador de la interfaz
        utm_serializer = LeadSourceSerializer(data=utm_payload)
        if any(utm_payload.values()) and not utm_serializer.is_valid():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(utm_serializer.errors)
            
        use_case = CreateLeadUseCase()
        lead = use_case.execute(
            tenant=tenant,
            lead_data=lead_data,
            utm_data=utm_payload,
            performed_by=self._username()
        )
        serializer.instance = lead

    def perform_destroy(self, instance):
        """Soft delete del lead: marca como eliminado y registra actividad."""
        use_case = DeleteLeadUseCase()
        use_case.execute(lead=instance, performed_by=self._username())

    def perform_update(self, serializer):
        """Actualiza un lead y registra el cambio de etapa cuando aplique."""
        old_stage = self.get_object().current_stage
        lead = serializer.save()
        new_stage = serializer.validated_data.get("current_stage", old_stage)
        
        use_case = ChangeLeadStageUseCase()
        use_case.execute(lead=lead, old_stage=old_stage, new_stage=new_stage, performed_by=self._username())

    @extend_schema(
        summary="Resumen IA del lead",
        description="Devuelve el último resumen generado por IA para el lead.",
        responses={200: LeadSummarySerializer, 404: OpenApiResponse(description="No hay resúmenes disponibles")},
    )
    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        """Entrega el ultimo resumen IA disponible para el lead solicitado."""
        lead = self.get_object()
        daily_summary = get_lead_summary(lead)
        if not daily_summary:
            return Response({"detail": "No hay resúmenes disponibles."}, status=404)
        serializer = LeadSummarySerializer(daily_summary)
        return Response(serializer.data)

    @extend_schema(
        summary="Estadísticas del pipeline",
        description="Métricas agregadas del pipeline de ventas: leads por etapa, tasas de conversión, etc.",
        parameters=[OpenApiParameter(name="tenant_slug", required=True, type=str)],
        responses={200: LeadsStatsSerializer},
    )
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

    @extend_schema(
        summary="Agregar nota",
        description="Registra una nota como actividad en el lead. A diferencia de add_activity, permite nota vacía.",
        request=inline_serializer("AddNote", fields={"note": serializers.CharField(required=False)}),
        responses={201: OpenApiResponse(description="Nota guardada")},
    )
    @action(detail=True, methods=["post"], url_path="add_note")
    def add_note(self, request, pk=None):
        """Registra una nota como actividad en el lead.

        POST /api/crm/leads/{id}/add_note/
        Body: {"note": "texto de la nota"}
        A diferencia de add_activity, permite nota vacía (para registro de movimiento).
        """
        lead = self.get_object()
        note = request.data.get("note", "").strip()
        use_case = AddNoteUseCase()
        use_case.execute(lead=lead, note=note, performed_by=self._username())
        return Response(
            {"detail": "Nota guardada."},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Agregar actividad",
        description="Registra una actividad manual en el lead.",
        request=inline_serializer("AddActivity", fields={"description": serializers.CharField()}),
        responses={201: OpenApiResponse(description="Actividad registrada correctamente")},
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
        use_case = AddActivityUseCase()
        use_case.execute(lead=lead, description=description, performed_by=self._username())
        return Response(
            {"detail": "Actividad registrada correctamente."},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Restaurar lead",
        description="Restaura un lead previamente eliminado (soft delete).",
        parameters=[OpenApiParameter(name="tenant_slug", required=True, type=str)],
        responses={200: OpenApiResponse(description="Lead restaurado correctamente")},
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
        use_case = RestoreLeadUseCase()
        use_case.execute(lead=lead, performed_by=self._username())
        return Response({"detail": "Lead restaurado correctamente."})

    @extend_schema(
        summary="Leads eliminados",
        description="Lista los leads en la papelera (soft delete) de un tenant.",
        parameters=[OpenApiParameter(name="tenant_slug", required=True, type=str)],
        responses={200: LeadSerializer(many=True)},
    )
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

    @extend_schema(
        summary="Reabrir lead (recompra)",
        description="Crea un nuevo lead a partir de uno cerrado. El lead original permanece cerrado.",
        parameters=[OpenApiParameter(name="tenant_slug", required=True, type=str)],
        responses={201: LeadDetailSerializer},
    )
    @action(detail=True, methods=["post"], url_path="reopen")
    def reopen(self, request, pk=None):
        """Crea un nuevo lead a partir de uno cerrado (recompra).

        POST /api/crm/leads/{id}/reopen/?tenant_slug=...
        El lead original permanece cerrado. Se crea un nuevo lead en la
        primera etapa del pipeline para el mismo contacto.
        """
        lead = self.get_object()
        use_case = ReopenLeadUseCase()
        try:
            new_lead = use_case.execute(lead=lead, performed_by=self._username())
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = LeadDetailSerializer(new_lead)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Listar/Crear tareas",
        description="GET lista las tareas del lead. POST crea una nueva tarea.",
        request=TaskSerializer,
        responses={200: TaskSerializer(many=True), 201: TaskSerializer},
    )
    @action(detail=True, methods=["get", "post"], url_path="tasks")
    def tasks(self, request, pk=None):
        """Lista o crea tareas para el lead.

        GET /api/crm/leads/{id}/tasks/
        POST /api/crm/leads/{id}/tasks/ — body: {description, due_date}
        """
        lead = self.get_object()
        if request.method == "GET":
            tasks_qs = lead.tasks.all().annotate(
                due_date_isnull=Case(
                    When(due_date__isnull=True, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ).order_by("due_date_isnull", "due_date", "-created_at")
            serializer = TaskSerializer(tasks_qs, many=True)
            return Response(serializer.data)
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(lead=lead)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Actualizar/Eliminar tarea",
        description="PATCH actualiza una tarea. DELETE la elimina.",
        request=TaskSerializer,
        responses={200: TaskSerializer, 204: OpenApiResponse(description="Tarea eliminada")},
    )
    @action(detail=True, methods=["patch", "delete"], url_path="tasks/(?P<task_id>[0-9]+)")
    def task_detail(self, request, pk=None, task_id=None):
        """Actualiza o elimina una tarea del lead.

        PATCH /api/crm/leads/{id}/tasks/{task_id}/ — body: {description, due_date, is_completed}
        DELETE /api/crm/leads/{id}/tasks/{task_id}/
        """
        lead = self.get_object()
        task = get_object_or_404(LeadTask, pk=task_id, lead=lead)
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

    @extend_schema(
        summary="Agregar etiqueta",
        description="Añade una etiqueta al lead.",
        request=inline_serializer("AddTag", fields={"tag_id": serializers.IntegerField()}),
        responses={201: LeadTagSerializer},
    )
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

    @extend_schema(
        summary="Quitar etiqueta",
        description="Elimina una etiqueta del lead.",
        request=inline_serializer("RemoveTag", fields={"tag_id": serializers.IntegerField()}),
        responses={200: OpenApiResponse(description="Etiqueta eliminada"), 404: OpenApiResponse(description="Etiqueta no encontrada")},
    )
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


@lru_cache(maxsize=128)
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


# ── Funciones auxiliares de analytics ──


@lru_cache(maxsize=1)
def _get_dept_coords() -> dict[str, tuple[float, float]]:
    """Carga coordenadas de departamentos desde CSV con cache de modulo.

    Returns:
        Dict mapeando nombre de departamento a (latitud, longitud).
    """
    import csv

    path = Path(__file__).resolve().parent.parent / "static" / "crm" / "data" / "departamentos_colombia.csv"
    coords: dict[str, tuple[float, float]] = {}
    try:
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row.get("nombre", "").strip()
                if name:
                    coords[name] = (float(row["latitud"]), float(row["longitud"]))
    except FileNotFoundError:
        pass
    return coords


def _get_pipeline_stats(
    leads_qs: models.QuerySet,
    pipeline_stages: list[dict],
) -> list[dict]:
    """Calcula el funnel de leads por etapa."""
    stage_counts = dict(
        leads_qs.values("current_stage")
        .annotate(count=Count("id"))
        .values_list("current_stage", "count")
    )
    funnel = []
    for stage in sorted(pipeline_stages, key=lambda s: s.get("order", 0)):
        funnel.append({
            "stage": stage.get("name", ""),
            "count": stage_counts.get(stage.get("name", ""), 0),
        })
    for stage_name in leads_qs.values_list("current_stage", flat=True).distinct():
        if not any(s.get("name") == stage_name for s in pipeline_stages):
            funnel.append({"stage": stage_name, "count": stage_counts.get(stage_name, 0)})
    return funnel


def _get_source_stats(leads_qs: models.QuerySet) -> tuple[list, list]:
    """Calcula distribucion de leads por fuente y por fuente+mes."""
    source_counts = list(
        leads_qs.filter(source__isnull=False)
        .values("source__platform")
        .annotate(count=Count("id"))
    )
    leads_by_source = [
        {"source": row["source__platform"] or "unknown", "count": row["count"]}
        for row in source_counts
    ]

    monthly_platforms = ["meta", "google", "tiktok", "web", "referral"]
    monthly_data = defaultdict(lambda: {p: 0 for p in monthly_platforms})
    source_monthly_counts = list(
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
    return leads_by_source, leads_by_source_monthly


def _get_timeline_stats(
    leads_qs: models.QuerySet,
    total_qs: models.QuerySet,
) -> dict:
    """Calcula tendencias temporales: leads por dia, won/lost, quotes, stage-date.

    Usa una sola consulta agrupada con anotaciones CASE/WHERE para won, lost y
    quotes, reemplazando las 4 consultas separadas del codigo original.
    """
    temporal_qs = (
        leads_qs.annotate(day=TruncDate("created_at"))
        .values("day", "current_stage")
        .annotate(
            total=Count("id"),
            won=Count(Case(When(is_closed=True, closed_result="won", then=1), output_field=IntegerField())),
            lost=Count(Case(When(is_closed=True, closed_result="lost", then=1), output_field=IntegerField())),
            quotes=Count(Case(When(current_stage__icontains="Cotizacion", then=1), output_field=IntegerField())),
        )
        .order_by("day")
    )
    temporal_data = list(temporal_qs)

    day_totals: dict[str, int] = {}
    day_won: dict[str, int] = {}
    day_lost: dict[str, int] = {}
    day_quotes: dict[str, int] = {}
    stage_by_date: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in temporal_data:
        day = row["day"]
        if day:
            day_key = day.strftime("%Y-%m-%d")
            day_totals[day_key] = day_totals.get(day_key, 0) + row["total"]
            day_won[day_key] = day_won.get(day_key, 0) + (row["won"] or 0)
            day_lost[day_key] = day_lost.get(day_key, 0) + (row["lost"] or 0)
            day_quotes[day_key] = day_quotes.get(day_key, 0) + (row["quotes"] or 0)
            stage = row["current_stage"] or "unknown"
            stage_by_date[day_key][stage] = row["total"]

    leads_by_day = [{"date": d, "count": day_totals[d]} for d in sorted(day_totals)]
    leads_by_stage_won = [{"date": d, "count": day_won[d]} for d in sorted(day_won) if day_won[d] > 0]
    leads_by_stage_lost = [{"date": d, "count": day_lost[d]} for d in sorted(day_lost) if day_lost[d] > 0]
    quotes_sent = [{"date": d, "count": day_quotes[d]} for d in sorted(day_quotes) if day_quotes[d] > 0]

    # Total leads by day (SIN filtro de fuente)
    total_temporal = (
        total_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    total_leads_by_day = [
        {"date": row["day"].strftime("%Y-%m-%d") if hasattr(row["day"], "strftime") else str(row["day"]), "count": row["count"]}
        for row in total_temporal
    ]

    return {
        "leads_by_day": leads_by_day,
        "total_leads_by_day": total_leads_by_day,
        "leads_by_stage_won": leads_by_stage_won,
        "leads_by_stage_lost": leads_by_stage_lost,
        "quotes_sent": quotes_sent,
        "stage_by_date": stage_by_date,
    }


def _get_regional_stats(leads_qs: models.QuerySet) -> dict:
    """Calcula distribucion regional (departamento) y datos geocodificados."""
    region_counts = list(
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

    # ── Geocoded heatmap ──
    dept_coords = _get_dept_coords()
    dept_counts: dict[str, int] = defaultdict(int)
    dept_won: dict[str, int] = defaultdict(int)
    dept_lost: dict[str, int] = defaultdict(int)

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

    return {
        "leads_by_region": leads_by_region,
        "leads_geocoded": leads_geocoded,
    }


def _get_kpi_progress(
    tenant,
    leads_qs: models.QuerySet,
    source_filter: str,
) -> tuple[list, str]:
    """Calcula el progreso de los KPI targets agrupados por periodo.

    En lugar de iterar target por target (N consultas), agrupa por
    ``period_type`` y calcula las metricas una sola vez por grupo,
    reduciendo las consultas de O(N) a O(tipos_de_periodo).
    """
    active_targets = list(
        KpiTarget.objects.filter(tenant=tenant, is_active=True)
        .select_related("metric")
    )

    period_label_months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    now_local = timezone.now()
    current_period_label = period_label_months[now_local.month - 1] + " " + str(now_local.year)

    if not active_targets:
        return [], current_period_label

    def _period_start(ptype: str):
        if ptype == "monthly":
            return now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ptype == "weekly":
            days_since_monday = now_local.weekday()
            return (now_local - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        if ptype == "quarterly":
            quarter_month = (now_local.month - 1) // 3 * 3 + 1
            return now_local.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        if ptype == "daily":
            return now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return None

    period_types = {t.period_type for t in active_targets}
    period_cache = {}

    for ptype in period_types:
        pstart = _period_start(ptype)
        if not pstart:
            continue
        base_qs = Lead.objects.filter(tenant=tenant, is_deleted=False, created_at__gte=pstart)
        if source_filter:
            base_qs = base_qs.filter(source__platform=source_filter)

        agg = base_qs.aggregate(
            total=Count("id"),
            won=Count(Case(When(is_closed=True, closed_result="won", then=1), output_field=IntegerField())),
        )
        won_leads = list(base_qs.filter(is_closed=True, closed_result="won"))
        won_count = agg["won"]

        revenue = 0.0
        avg_days = 0.0
        durations = []
        for wl in won_leads:
            revenue += float(getattr(wl, "computed_value", 0) or 0)
            if wl.created_at and wl.updated_at:
                durations.append((wl.updated_at - wl.created_at).total_seconds() / 86400)
        if durations:
            avg_days = sum(durations) / len(durations)

        active_qs = list(base_qs.filter(is_closed=False))
        pipeline_val = sum(float(getattr(al, "computed_value", 0) or 0) for al in active_qs)

        period_cache[ptype] = {
            "total": agg["total"],
            "won": won_count,
            "revenue": revenue,
            "avg_days": avg_days,
            "pipeline_value": pipeline_val,
        }

    kpi_targets_data = []
    for target in active_targets:
        pc = period_cache.get(target.period_type, {})
        metric = target.metric
        current_value = 0.0

        if target.metric_type == "leads":
            current_value = float(pc.get("total", 0))
        elif target.metric_type == "conversions":
            current_value = float(pc.get("won", 0))
        elif target.metric_type == "conversion_rate":
            total = pc.get("total", 0)
            won = pc.get("won", 0)
            current_value = round((won / total) * 100, 1) if total > 0 else 0.0
        elif target.metric_type == "avg_days":
            current_value = round(pc.get("avg_days", 0), 1)
        elif target.metric_type == "revenue":
            current_value = round(pc.get("revenue", 0), 0)
        elif target.metric_type == "avg_deal_value":
            won = pc.get("won", 0)
            revenue = pc.get("revenue", 0)
            current_value = round(revenue / won, 0) if won > 0 else 0.0
        elif target.metric_type == "pipeline_value":
            current_value = round(pc.get("pipeline_value", 0), 0)
        elif target.metric_type in ("quotes_sent", "quotes_accepted", "leads_per_day",
                                    "retention_rate", "follow_up_rate", "new_contacts",
                                    "emails_sent", "calls_made", "meetings_scheduled",
                                    "cost_per_lead", "roi"):
            current_value = 0.0

        progress_percent = round((current_value / target.target_value) * 100, 1) if target.target_value > 0 else 0.0
        kpi_targets_data.append({
            "id": target.id,
            "metric_type": metric.slug if metric else "",
            "name": metric.name if metric else "",
            "metric_name": metric.name if metric else "",
            "metric_unit": metric.unit if metric else "",
            "metric_icon": metric.icon if metric else "",
            "metric_color": metric.color if metric else "",
            "metric_category": metric.category if metric else "",
            "target_value": target.target_value,
            "current_value": current_value,
            "progress_percent": progress_percent,
            "period_type": target.period_type,
            "is_active": target.is_active,
        })

    return kpi_targets_data, current_period_label


def _get_summary(leads_qs, total_leads, won_leads, timeline):
    """Calcula las metricas de resumen del pipeline."""
    conversion_rate = (won_leads / total_leads) if total_leads > 0 else 0

    week_start = timezone.now() - timedelta(days=7)
    leads_this_week = leads_qs.filter(created_at__gte=week_start).count()
    lost_leads = leads_qs.filter(is_closed=True, closed_result="lost").count()
    quotes_sent_count = leads_qs.filter(current_stage__icontains="Cotizacion").count()

    closed_won = list(leads_qs.filter(is_closed=True, closed_result="won"))
    durations = [
        (lead.updated_at - lead.created_at).total_seconds() / 86400
        for lead in closed_won
        if lead.created_at and lead.updated_at
    ]
    avg_days = sum(durations) / len(durations) if durations else 0

    revenue = 0.0
    for wl in closed_won:
        revenue += float(getattr(wl, "computed_value", 0) or 0)
    revenue = round(revenue, 0)

    avg_deal_value = round(revenue / len(closed_won), 0) if closed_won else 0.0

    active_leads = list(leads_qs.filter(is_closed=False))
    pipeline_value = sum(float(getattr(al, "computed_value", 0) or 0) for al in active_leads)
    pipeline_value = round(pipeline_value, 0)

    return {
        "total_leads": total_leads,
        "won_leads": won_leads,
        "lost_leads": lost_leads,
        "quotes_sent_count": quotes_sent_count,
        "conversion_rate": round(conversion_rate, 3),
        "avg_days_to_close": round(avg_days, 1),
        "leads_this_week": leads_this_week,
        "revenue": revenue,
        "avg_deal_value": avg_deal_value,
        "pipeline_value": pipeline_value,
    }


@extend_schema(
    summary="Analíticas del pipeline",
    description="Métricas detalladas del pipeline: funnel, leads por fuente, tendencias, KPIs.",
    parameters=[
        OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str),
        OpenApiParameter(name="days", description="Ventana en días (default 30)", type=int),
        OpenApiParameter(name="source", description="Filtrar por plataforma", type=str),
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
def analytics_api(request, tenant_slug: str):
    """API de analíticas del pipeline.

    Query params:
        days: int (default 30) — filtra leads creados en los últimos N días.
        source: str (opcional) — filtra por LeadSource.platform.

    Returns JSON con funnel, leads_by_source, leads_by_day y summary.

    La implementación delega en 6 funciones auxiliares modulares
    (``_get_pipeline_stats``, ``_get_source_stats``, ``_get_timeline_stats``,
    ``_get_regional_stats``, ``_get_kpi_progress``, ``_get_summary``) que
    consolidan consultas y evitan duplicación de lógica.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

    days = int(request.query_params.get("days", 30))
    offset = int(request.query_params.get("offset", 0))
    source_filter = request.query_params.get("source", "").strip()

    since = timezone.now() - timedelta(days=days + (offset * days))
    until = timezone.now() - timedelta(days=(offset * days)) if offset > 0 else None

    leads_qs = Lead.objects.filter(
        tenant=tenant, is_deleted=False, created_at__gte=since,
    )
    if until:
        leads_qs = leads_qs.filter(created_at__lte=until)
    if source_filter:
        leads_qs = leads_qs.filter(source__platform=source_filter)

    total_qs = Lead.objects.filter(
        tenant=tenant, is_deleted=False, created_at__gte=since,
    )
    if until:
        total_qs = total_qs.filter(created_at__lte=until)

    try:
        pipeline_stages = list(tenant.pipeline_config.stages or [])
    except Exception:
        pipeline_stages = []

    funnel = _get_pipeline_stats(leads_qs, pipeline_stages)
    leads_by_source, leads_by_source_monthly = _get_source_stats(leads_qs)

    timeline = _get_timeline_stats(leads_qs, total_qs)
    timeline["stage_by_date"] = {
        day: dict(stages) for day, stages in timeline["stage_by_date"].items()
    }
    regional = _get_regional_stats(leads_qs)

    total_leads = leads_qs.count()
    won_leads = leads_qs.filter(is_closed=True, closed_result="won").count()

    summary = _get_summary(leads_qs, total_leads, won_leads, timeline)
    kpi_targets_data, current_period_label = _get_kpi_progress(tenant, leads_qs, source_filter)

    stage_by_date = timeline["stage_by_date"]
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
        "leads_by_day": timeline["leads_by_day"],
        "total_leads_by_day": timeline["total_leads_by_day"],
        "leads_by_stage_won": timeline["leads_by_stage_won"],
        "leads_by_stage_lost": timeline["leads_by_stage_lost"],
        "quotes_sent": timeline["quotes_sent"],
        "leads_by_region": regional["leads_by_region"],
        "leads_geocoded": regional["leads_geocoded"],
        "leads_by_source_monthly": leads_by_source_monthly,
        "leads_by_stage": leads_by_stage,
        "pipeline_stages": pipeline_stages,
        "summary": summary,
        "kpi_targets": kpi_targets_data,
        "current_period_label": current_period_label,
    })


@extend_schema(
    summary="Listar/Crear etiquetas",
    description="GET lista etiquetas del tenant. POST crea una nueva.",
    parameters=[OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str)],
    request=TagSerializer,
    responses={200: TagSerializer(many=True), 201: TagSerializer},
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
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


@extend_schema(
    summary="Eliminar etiqueta",
    description="Elimina una etiqueta no predefinida.",
    parameters=[
        OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str),
        OpenApiParameter(name="tag_id", location=OpenApiParameter.PATH, type=int),
    ],
    responses={204: OpenApiResponse(description="Etiqueta eliminada")},
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
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


@extend_schema(
    summary="Listar/Crear metas KPI",
    description="GET lista metas KPI del tenant. POST crea una nueva meta.",
    parameters=[OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str)],
    request=KpiTargetCreateSerializer,
    responses={200: KpiTargetSerializer(many=True), 201: KpiTargetSerializer},
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
def kpi_targets_list_create(request, tenant_slug):
    """Lista o crea metas KPI para un tenant.

    GET /api/crm/tenants/{slug}/kpi-targets/ — lista todas las metas
    POST /api/crm/tenants/{slug}/kpi-targets/ — crea una meta
    Body POST: {metric_type: str, target_value: float, period_type: str}
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

    if request.method == "GET":
        targets = KpiTarget.objects.filter(tenant=tenant).select_related("metric").order_by("metric__sort_order", "period_type")
        serializer = KpiTargetSerializer(targets, many=True)
        return Response(serializer.data)

    metric_slug = request.data.get("metric_type", "").strip()
    if not metric_slug:
        return Response({"metric_type": "Este campo es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

    metric = get_object_or_404(KpiMetricType, slug=metric_slug, is_active=True)
    period_type = request.data.get("period_type", "monthly")
    KpiTarget.objects.filter(tenant=tenant, metric=metric, period_type=period_type).delete()

    serializer = KpiTargetCreateSerializer(
        data={"metric_type": metric_slug, "target_value": request.data.get("target_value"), "period_type": period_type},
        context={"tenant": tenant}
    )
    if serializer.is_valid():
        target = serializer.save()
        out = KpiTargetSerializer(target).data
        return Response(out, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Detalle de meta KPI",
    description="GET obtiene, PATCH actualiza, DELETE elimina una meta KPI.",
    parameters=[
        OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str),
        OpenApiParameter(name="target_id", location=OpenApiParameter.PATH, type=int),
    ],
    responses={200: KpiTargetSerializer, 204: OpenApiResponse(description="Meta eliminada")},
)
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
def kpi_target_detail(request, tenant_slug, target_id):
    """Obtiene, actualiza o elimina una meta KPI.

    GET /api/crm/tenants/{slug}/kpi-targets/{id}/
    PATCH /api/crm/tenants/{slug}/kpi-targets/{id}/ — actualizacion parcial
    DELETE /api/crm/tenants/{slug}/kpi-targets/{id}/
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
    target = get_object_or_404(KpiTarget, pk=target_id, tenant=tenant)

    if request.method == "GET":
        serializer = KpiTargetSerializer(target)
        return Response(serializer.data)

    if request.method == "PATCH":
        metric_slug = request.data.get("metric_type", "").strip()
        new_metric = None
        if metric_slug and target.metric_id != metric_slug:
            new_metric = get_object_or_404(KpiMetricType, slug=metric_slug, is_active=True)
        new_period = request.data.get("period_type", "").strip()
        changes_metric = new_metric is not None
        changes_period = new_period and new_period != target.period_type
        if changes_metric or changes_period:
            eff_metric = new_metric if new_metric else target.metric
            eff_period = new_period or target.period_type
            KpiTarget.objects.filter(
                tenant=tenant, metric=eff_metric, period_type=eff_period
            ).exclude(pk=target.pk).delete()
        if new_metric:
            target.metric = new_metric
        if "target_value" in request.data:
            target.target_value = float(request.data["target_value"])
        if "period_type" in request.data:
            target.period_type = request.data["period_type"]
        if "is_active" in request.data:
            target.is_active = bool(request.data["is_active"])
        target.save()
        return Response(KpiTargetSerializer(target).data)

    target.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Listar/Crear productos",
    description="GET lista productos del tenant. POST crea un nuevo producto.",
    parameters=[OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str)],
    request=ProductCreateSerializer,
    responses={200: ProductSerializer(many=True), 201: ProductSerializer},
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
def products_list_create(request, tenant_slug):
    """Lista o crea productos para un tenant.

    GET /api/crm/tenants/{slug}/products/ — lista productos activos
    POST /api/crm/tenants/{slug}/products/ — crea un producto
    Body POST: {name, sku, description, price, cost, is_active}
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

    if request.method == "GET":
        products = Product.objects.filter(tenant=tenant).order_by("name")
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    serializer = ProductCreateSerializer(data=request.data, context={"tenant": tenant})
    if serializer.is_valid():
        product = serializer.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Detalle de producto",
    description="GET obtiene, PATCH actualiza, DELETE elimina un producto.",
    parameters=[
        OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str),
        OpenApiParameter(name="product_id", location=OpenApiParameter.PATH, type=int),
    ],
    request=ProductSerializer,
    responses={200: ProductSerializer, 204: OpenApiResponse(description="Producto eliminado")},
)
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
def product_detail(request, tenant_slug, product_id):
    """Obtiene, actualiza o elimina un producto.

    GET/PATCH/DELETE /api/crm/tenants/{slug}/products/{id}/
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
    product = get_object_or_404(Product, pk=product_id, tenant=tenant)

    if request.method == "GET":
        return Response(ProductSerializer(product).data)

    if request.method == "PATCH":
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    product.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Listar/Agregar productos a lead",
    description="GET lista productos asociados al lead. POST agrega un producto.",
    parameters=[
        OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str),
        OpenApiParameter(name="lead_id", location=OpenApiParameter.PATH, type=int),
    ],
    request=LeadProductCreateSerializer,
    responses={200: LeadProductSerializer(many=True), 201: LeadProductSerializer},
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
def lead_products_list_create(request, tenant_slug, lead_id):
    """Lista o agrega productos a un lead.

    GET /api/crm/leads/{id}/products/ — lista productos del lead
    POST /api/crm/leads/{id}/products/ — agrega producto al lead
    Body POST: {product_id, quantity, unit_price_override, notes}
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
    lead = get_object_or_404(Lead, pk=lead_id, tenant=tenant)

    if request.method == "GET":
        products = lead.lead_products.select_related("product").all()
        serializer = LeadProductSerializer(products, many=True)
        return Response(serializer.data)

    serializer = LeadProductCreateSerializer(data=request.data, context={"lead": lead})
    if serializer.is_valid():
        lp = serializer.save()
        return Response(LeadProductSerializer(lp).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Actualizar/Eliminar producto de lead",
    description="PATCH actualiza un producto asociado al lead. DELETE lo elimina.",
    parameters=[
        OpenApiParameter(name="tenant_slug", location=OpenApiParameter.PATH, type=str),
        OpenApiParameter(name="lead_id", location=OpenApiParameter.PATH, type=int),
        OpenApiParameter(name="product_id", location=OpenApiParameter.PATH, type=int),
    ],
    request=LeadProductSerializer,
    responses={200: LeadProductSerializer, 204: OpenApiResponse(description="Producto eliminado del lead")},
)
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@require_tenant_access()
def lead_product_detail(request, tenant_slug, lead_id, product_id):
    """Actualiza o elimina un producto de un lead.

    PATCH /api/crm/leads/{lead_id}/products/{product_id}/
    DELETE /api/crm/leads/{lead_id}/products/{product_id}/
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
    lead = get_object_or_404(Lead, pk=lead_id, tenant=tenant)
    lp = get_object_or_404(lead.lead_products, pk=product_id)

    if request.method == "PATCH":
        serializer = LeadProductSerializer(lp, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    lp.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)