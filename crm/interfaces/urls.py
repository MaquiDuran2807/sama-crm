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
    kpi_targets_list_create,
    kpi_target_detail,
    products_list_create,
    product_detail,
    lead_products_list_create,
    lead_product_detail,
)

router = DefaultRouter()
router.register(r"contacts", ContactViewSet, basename="contact")
router.register(r"leads", LeadViewSet, basename="lead")

urlpatterns = [
    path("webhook/chat/", webhook_sync_contact, name="webhook-sync-contact"),
    path("tenants/<slug:tenant_slug>/analytics/", analytics_api, name="analytics-api"),
    path("tenants/<slug:tenant_slug>/tags/", tags_list_create, name="tags-list-create"),
    path("tenants/<slug:tenant_slug>/tags/<int:tag_id>/", tag_delete, name="tag-delete"),
    path("tenants/<slug:tenant_slug>/kpi-targets/", kpi_targets_list_create, name="kpi-targets-list-create"),
    path("tenants/<slug:tenant_slug>/kpi-targets/<int:target_id>/", kpi_target_detail, name="kpi-target-detail"),
    path("tenants/<slug:tenant_slug>/products/", products_list_create, name="products-list-create"),
    path("tenants/<slug:tenant_slug>/products/<int:product_id>/", product_detail, name="product-detail"),
    path("leads/<int:lead_id>/products/", lead_products_list_create, name="lead-products-list-create"),
    path("leads/<int:lead_id>/products/<int:product_id>/", lead_product_detail, name="lead-product-detail"),
    path("", include(router.urls)),
]