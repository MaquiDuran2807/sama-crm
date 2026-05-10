"""Rutas REST de la app `crm`.

Expone los endpoints de contactos, leads y etiquetas mediante un router de DRF
para que las acciones de la capa de interfaces queden centralizadas y consistentes.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from crm.interfaces.views import (
    ContactViewSet,
    LeadViewSet,
    webhook_sync_contact,
    analytics_api,
    tags_list_create,
    tag_delete,
)

router = DefaultRouter()
router.register(r"contacts", ContactViewSet, basename="contact")
router.register(r"leads", LeadViewSet, basename="lead")

urlpatterns = [
    path("webhook/chat/", webhook_sync_contact, name="webhook-sync-contact"),
    path("tenants/<slug:tenant_slug>/analytics/", analytics_api, name="analytics-api"),
    path("tenants/<slug:tenant_slug>/tags/", tags_list_create, name="tags-list-create"),
    path("tenants/<slug:tenant_slug>/tags/<int:tag_id>/", tag_delete, name="tag-delete"),
    path("", include(router.urls)),
]