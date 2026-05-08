"""Vistas REST de la app `tenants`.

Este modulo adapta las peticiones HTTP a las operaciones del dominio de
tenants: listado de clientes, detalle, pipeline comercial, modulos activos y
campos personalizados. La capa de interfaces solo coordina entrada/salida y no
contiene reglas de negocio duras.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from tenants.domain.models import Tenant, TenantModule, PipelineConfig, CustomField
from tenants.domain.services import is_subscription_active, get_active_modules, get_custom_fields
from tenants.interfaces.serializers import (
    TenantSerializer,
    TenantDetailSerializer,
    TenantModuleSerializer,
    PipelineConfigSerializer,
    CustomFieldSerializer,
)


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para tenants.

    Attributes:
        queryset: Base de datos de tenants activos.
        lookup_field: Campo usado por DRF para resolver el detalle por slug.
    """
    queryset = Tenant.objects.filter(is_active=True)
    lookup_field = "slug"

    def get_serializer_class(self):
        """Selecciona el serializador en funcion de la accion actual.

        Returns:
            `TenantDetailSerializer` cuando se solicita el detalle y
            `TenantSerializer` para la lista resumida.
        """

        if self.action == "retrieve":
            return TenantDetailSerializer
        return TenantSerializer

    @action(detail=True, methods=["get"], url_path="pipeline")
    def pipeline(self, request, slug=None):
        """Entrega la configuracion del pipeline del tenant.

        Args:
            request: Objeto HTTP de DRF. No se usa directamente, pero lo
                recibe la accion decorada por `@action`.
            slug: Identificador publico del tenant extraido de la URL.
        """
        tenant = self.get_object()
        pipeline_config = get_object_or_404(PipelineConfig, tenant=tenant)
        serializer = PipelineConfigSerializer(pipeline_config)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="modules")
    def modules(self, request, slug=None):
        """Entrega los modulos activos del tenant.

        Args:
            request: Peticion HTTP entrante de DRF.
            slug: Slug publico del tenant; llega en la ruta aunque aqui se
                resuelve a traves de `self.get_object()`.
        """
        tenant = self.get_object()
        modules = get_active_modules(tenant)
        serializer = TenantModuleSerializer(modules, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="custom-fields")
    def custom_fields(self, request, slug=None):
        """Entrega los campos personalizados del tenant filtrados por modelo.

        Args:
            request: Peticion HTTP desde el cliente REST.
            slug: Slug del tenant resuelto por el router.
        """
        tenant = self.get_object()
        target_model = request.query_params.get("target_model", "contact")
        fields = get_custom_fields(tenant, target_model)
        serializer = CustomFieldSerializer(fields, many=True)
        return Response(serializer.data)