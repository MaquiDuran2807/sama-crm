"""Vistas de la app `crm`.

Este modulo contiene tanto las vistas REST de la API como las vistas HTML que
renderizan el dashboard Kanban y el detalle de lead del CRM. La capa de
interfaces recibe peticiones HTTP y las traduce a operaciones del dominio:
crear/editar contactos, crear/editar leads, registrar cambios de etapa,
obtener resenas IA y calcular metricas del pipeline.
"""

from collections import defaultdict

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views import View
from django.utils import timezone

from tenants.domain.models import Tenant
from tenants.domain.services import get_pipeline_stages
from crm.domain.models import Contact, Lead, LeadSource, LeadActivity
from crm.domain.services import change_lead_stage, get_leads_stats, get_lead_summary
from crm.domain.contact_sync import sync_contact_from_whatsapp
from crm.interfaces.serializers import (
    ContactSerializer,
    LeadSerializer,
    LeadDetailSerializer,
    LeadCreateSerializer,
    LeadSummarySerializer,
    LeadsStatsSerializer,
)


@api_view(["POST"])
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
    def get_serializer_class(self):
        """Selecciona el serializador apropiado segun la accion de DRF."""

        if self.action == "create":
            return LeadCreateSerializer
        if self.action == "retrieve":
            return LeadDetailSerializer
        return LeadSerializer

    def get_queryset(self):
        """Devuelve los leads del tenant filtrando por etapa o contacto."""

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

        return qs.select_related("contact", "tenant")

    def perform_create(self, serializer):
        """Crea un lead y, si corresponde, su fuente de origen asociada."""

        tenant_slug = self.request.query_params.get("tenant_slug")
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        lead = serializer.save(tenant=tenant)

        # Si vienen datos de fuente (UTM), crear LeadSource automáticamente
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

    def perform_update(self, serializer):
        """Actualiza un lead y registra el cambio de etapa cuando aplique."""

        old_stage = self.get_object().current_stage
        new_stage = serializer.validated_data.get("current_stage", old_stage)
        lead = serializer.save()

        # Si cambió la etapa, usar el servicio de dominio para registrar la actividad
        if old_stage != new_stage:
            change_lead_stage(lead, new_stage, performed_by="user")

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        """Entrega el ultimo resumen IA disponible para el lead solicitado.

        Args:
            request: Peticion HTTP de lectura.
            pk: Identificador primario del lead extraido de la URL.
        """
        lead = self.get_object()
        daily_summary = get_lead_summary(lead)
        if not daily_summary:
            return Response({"detail": "No hay resúmenes disponibles."}, status=404)
        serializer = LeadSummarySerializer(daily_summary)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Devuelve metricas agregadas del pipeline para el tenant indicado.

        Args:
            request: Peticion HTTP que aporta el query param `tenant_slug`.
        """
        tenant_slug = request.query_params.get("tenant_slug")
        if not tenant_slug:
            return Response({"detail": "tenant_slug es obligatorio."}, status=400)
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        stats = get_leads_stats(tenant)
        serializer = LeadsStatsSerializer(stats)
        return Response(serializer.data)


def _format_time_since(updated_at):
    """Formatea el tiempo transcurrido desde la ultima actualizacion.

    Args:
        updated_at: Marca temporal del ultimo cambio registrado en el lead.

    Returns:
        Cadena legible para mostrar en la tarjeta del dashboard.
    """

    delta = timezone.now() - updated_at
    if delta.days > 0:
        return f"hace {delta.days} días"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"hace {hours}h"
    minutes = max(delta.seconds // 60, 1)
    return f"hace {minutes} min"


class CrmDashboardTemplateView(View):
    """Vista HTML del dashboard Kanban del CRM.

    Args de la ruta:
        tenant_slug: Slug publico del tenant que define el contexto comercial
            a visualizar en el tablero.
    """

    template_name = "crm/dashboard.html"

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
            Lead.objects.filter(tenant=tenant)
            .select_related("contact")
            .order_by("current_stage", "-updated_at")
        )

        leads_by_stage = defaultdict(list)
        for lead in leads:
            lead.time_since_update = _format_time_since(lead.updated_at)
            lead.is_new = lead.created_at.date() == timezone.localdate()
            leads_by_stage[lead.current_stage].append(lead)

        pipeline = []
        for stage in stages:
            stage_name = stage.get("name", "")
            stage_leads = leads_by_stage.get(stage_name, [])
            pipeline.append(
                {
                    "name": stage_name,
                    "color": stage.get("color", "#64748b"),
                    "order": stage.get("order", 0),
                    "lead_count": len(stage_leads),
                    "leads": stage_leads,
                }
            )

        context = {
            "tenant": tenant,
            "stats": stats,
            "pipeline": pipeline,
        }
        return render(request, self.template_name, context)


class CrmLeadDetailTemplateView(View):
    """Vista HTML de detalle para un lead concreto del CRM.

    Args de la ruta:
        tenant_slug: Slug del tenant dueño del lead.
        lead_id: Identificador numérico del lead a renderizar.
    """

    template_name = "crm/lead_detail.html"

    def get(self, request, tenant_slug: str, lead_id: int, *args, **kwargs):
        """Construye el contexto del detalle del lead y su actividad asociada."""

        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
        lead = get_object_or_404(
            Lead.objects.select_related("contact", "tenant").prefetch_related("activities"),
            pk=lead_id,
            tenant=tenant,
        )
        summary = get_lead_summary(lead)

        context = {
            "tenant": tenant,
            "lead": lead,
            "summary": summary,
            "activities": lead.activities.all(),
        }
        return render(request, self.template_name, context)