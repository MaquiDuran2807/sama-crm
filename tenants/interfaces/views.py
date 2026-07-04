"""Vistas REST de la app `tenants`.

Este modulo adapta las peticiones HTTP a las operaciones del dominio de
tenants: listado de clientes, detalle, pipeline comercial, modulos activos y
campos personalizados. La capa de interfaces solo coordina entrada/salida y no
contiene reglas de negocio duras.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from tenants.domain.models import Tenant, TenantModule, PipelineConfig, CustomField, TenantUser
from tenants.domain.services import is_subscription_active, get_active_modules, get_custom_fields
from tenants.application.use_cases import (
    GetTenantModulesUseCase,
    UpdatePipelineConfigUseCase,
    ValidateSubscriptionUseCase,
)
from tenants.interfaces.serializers import (
    TenantSerializer,
    TenantDetailSerializer,
    TenantModuleSerializer,
    PipelineConfigSerializer,
    CustomFieldSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="Listar tenants", description="Devuelve los tenants a los que el usuario tiene acceso."),
    retrieve=extend_schema(summary="Obtener tenant", description="Detalle completo de un tenant por slug."),
    update=extend_schema(summary="Actualizar tenant"),
    partial_update=extend_schema(summary="Actualizar parcialmente tenant"),
    destroy=extend_schema(summary="Eliminar tenant"),
)
class TenantViewSet(viewsets.ModelViewSet):
    """ViewSet para tenants (lectura + actualizacion de pipeline).

    Attributes:
        queryset: Base de datos de tenants activos filtrados por acceso del usuario.
        lookup_field: Campo usado por DRF para resolver el detalle por slug.
    """
    lookup_field = "slug"
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtra tenants a los que el usuario autenticado tiene membresia.

        Los superusuarios pueden ver todos los tenants activos.
        """
        qs = Tenant.objects.filter(is_active=True)
        user = self.request.user
        if user and getattr(user, "is_superuser", False):
            return qs
        return qs.filter(memberships__user=user)

    def get_serializer_class(self):
        """Selecciona el serializador en funcion de la accion actual.

        Returns:
            `TenantDetailSerializer` cuando se solicita el detalle y
            `TenantSerializer` para la lista resumida.
        """

        if self.action == "retrieve":
            return TenantDetailSerializer
        return TenantSerializer

    @extend_schema(summary="Pipeline del tenant", description="Configuración de etapas del pipeline comercial.")
    @action(detail=True, methods=["get"], url_path="pipeline")
    def pipeline(self, request, slug=None):
        """Entrega la configuracion del pipeline del tenant."""
        tenant = self.get_object()
        pipeline_config = get_object_or_404(PipelineConfig, tenant=tenant)
        serializer = PipelineConfigSerializer(pipeline_config)
        return Response(serializer.data)

    @extend_schema(summary="Módulos activos", description="Lista los módulos habilitados para el tenant.")
    @action(detail=True, methods=["get"], url_path="modules")
    def modules(self, request, slug=None):
        """Entrega los modulos activos del tenant."""
        tenant = self.get_object()
        use_case = GetTenantModulesUseCase()
        modules = use_case.execute(tenant)
        serializer = TenantModuleSerializer(modules, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Campos personalizados",
        description="Lista los campos personalizados del tenant, filtrados opcionalmente por target_model.",
        parameters=[OpenApiParameter(name="target_model", description="Modelo destino (contact, lead)", type=str)],
    )
    @action(detail=True, methods=["get"], url_path="custom-fields")
    def custom_fields(self, request, slug=None):
        """Entrega los campos personalizados del tenant filtrados por modelo."""
        tenant = self.get_object()
        target_model = request.query_params.get("target_model", "contact")
        fields = get_custom_fields(tenant, target_model)
        serializer = CustomFieldSerializer(fields, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Pipeline config",
        description="GET para leer, PATCH para actualizar la configuración del pipeline.",
        request=PipelineConfigSerializer,
    )
    @action(detail=True, methods=["get", "patch"], url_path="pipeline-config")
    def pipeline_config_update(self, request, slug=None):
        """API unificada de pipeline: GET para leer, PATCH para actualizar."""
        tenant = self.get_object()
        pipeline_config = get_object_or_404(PipelineConfig, tenant=tenant)

        if request.method == "GET":
            serializer = PipelineConfigSerializer(pipeline_config)
            return Response(serializer.data)

        stages_data = request.data.get("stages")
        use_case = UpdatePipelineConfigUseCase()
        try:
            pipeline_config = use_case.execute(tenant, stages_data)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PipelineConfigSerializer(pipeline_config)
        return Response(serializer.data)