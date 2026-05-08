"""Rutas REST de la app `crm`.

Expone los endpoints de contactos y leads mediante un router de DRF para que
las acciones de la capa de interfaces queden centralizadas y consistentes.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from crm.interfaces.views import ContactViewSet, LeadViewSet, webhook_sync_contact

router = DefaultRouter()
router.register(r"contacts", ContactViewSet, basename="contact")
router.register(r"leads", LeadViewSet, basename="lead")

urlpatterns = [
    path("webhook/chat/", webhook_sync_contact, name="webhook-sync-contact"),
    path("", include(router.urls)),
]