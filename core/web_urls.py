"""Rutas públicas web de la app core.

Expone las rutas para el sitio web principal de SAMA.
"""

from django.urls import path
from core.interfaces.web_views import (
    HomePageView,
    LoginView,
    LogoutView,
    DashboardView,
    FeaturesView,
    PricingView,
    AboutView,
    ContactView,
)

urlpatterns = [
    path("", HomePageView.as_view(), name="core-home"),
    path("account/login/", LoginView.as_view(), name="core-login"),
    path("account/logout/", LogoutView.as_view(), name="core-logout"),
    path("dashboard/", DashboardView.as_view(), name="core-dashboard"),
    path("features/", FeaturesView.as_view(), name="core-features"),
    path("pricing/", PricingView.as_view(), name="core-pricing"),
    path("about/", AboutView.as_view(), name="core-about"),
    path("contact/", ContactView.as_view(), name="core-contact"),
]