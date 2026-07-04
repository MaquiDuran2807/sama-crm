"""Vistas de la app core (API REST).

Este módulo contiene las vistas REST para gestión de páginas, secciones,
configuración del sitio y mensajes de contacto.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from tenants.domain.models import Tenant
from core.domain.models import SiteConfiguration, Page, Section, MenuItem, ContactMessage
from core.domain.services import get_site_config, get_page_sections
from core.interfaces.serializers import (
    SiteConfigurationSerializer,
    PageSerializer,
    PageListSerializer,
    SectionSerializer,
    MenuItemSerializer,
    ContactMessageSerializer,
    ContactMessageCreateSerializer,
)


class SiteConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet para SiteConfiguration."""

    serializer_class = SiteConfigurationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.tenant:
            return SiteConfiguration.objects.filter(tenant=user.tenant)
        return SiteConfiguration.objects.none()


class PageViewSet(viewsets.ModelViewSet):
    """ViewSet para páginas."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return PageListSerializer
        return PageSerializer

    def get_queryset(self):
        user = self.request.user
        if user.tenant:
            return Page.objects.filter(tenant=user.tenant)
        return Page.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=False, methods=["get"])
    def published(self, request):
        """Lista todas las páginas publicadas."""
        user = request.user
        if not user.tenant:
            return Response({"detail": "No tenant associated"}, status=status.HTTP_400_BAD_REQUEST)

        pages = Page.objects.filter(
            tenant=user.tenant,
            status=Page.PageStatus.PUBLISHED,
        ).order_by("order", "-created_at")

        serializer = PageListSerializer(pages, many=True)
        return Response(serializer.data)


class SectionViewSet(viewsets.ModelViewSet):
    """ViewSet para secciones."""

    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.tenant:
            return Section.objects.filter(page__tenant=user.tenant)
        return Section.objects.none()


class MenuItemViewSet(viewsets.ModelViewSet):
    """ViewSet para elementos del menú."""

    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.tenant:
            return MenuItem.objects.filter(tenant=user.tenant)
        return MenuItem.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class ContactMessageViewSet(viewsets.ModelViewSet):
    """ViewSet para mensajes de contacto."""

    serializer_class = ContactMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.tenant:
            return ContactMessage.objects.filter(tenant=user.tenant)
        return ContactMessage.objects.none()

    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request):
        """Cuenta los mensajes sin leer."""
        user = request.user
        if not user.tenant:
            return Response({"count": 0})

        count = ContactMessage.objects.filter(
            tenant=user.tenant,
            status=ContactMessage.Status.NEW,
        ).count()

        return Response({"count": count})