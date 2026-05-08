"""Rutas web HTML de la app `crm`.

Este modulo expone las paginas visuales del CRM, separadas de la API REST para
mantener limpia la arquitectura hexagonal: aqui viven las pantallas del
backend web, no los endpoints JSON.
"""

from django.urls import path

from crm.interfaces.views import CrmDashboardTemplateView, CrmLeadDetailTemplateView

app_name = "crm_web"

urlpatterns = [
    path("<slug:tenant_slug>/dashboard/", CrmDashboardTemplateView.as_view(), name="dashboard"),
    path(
        "<slug:tenant_slug>/leads/<int:lead_id>/",
        CrmLeadDetailTemplateView.as_view(),
        name="lead-detail",
    ),
]
