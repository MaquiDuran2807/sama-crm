"""Rutas REST de la app `tenants`.

El router expone el `TenantViewSet` y sus acciones adicionales para pipeline,
modulos activos y campos personalizados.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tenants.interfaces.views import TenantViewSet

router = DefaultRouter()
router.register(r"tenants", TenantViewSet, basename="tenant")

urlpatterns = [
    path("", include(router.urls)),
]