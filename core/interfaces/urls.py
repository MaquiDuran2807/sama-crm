"""Rutas de la app core.

Contiene tanto las rutas de la API REST como las rutas públicas del sitio web.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.interfaces.views import (
    SiteConfigurationViewSet,
    PageViewSet,
    SectionViewSet,
    MenuItemViewSet,
    ContactMessageViewSet,
)
from core.interfaces.web_views import (
    HomePageView,
    PageView,
    ContactPageView,
    LandingPageView,
    ComingSoonView,
    ContactSubmitView,
)

router = DefaultRouter()
router.register(r"config", SiteConfigurationViewSet, basename="site-config")
router.register(r"pages", PageViewSet, basename="page")
router.register(r"sections", SectionViewSet, basename="section")
router.register(r"menu", MenuItemViewSet, basename="menu-item")
router.register(r"messages", ContactMessageViewSet, basename="contact-message")

urlpatterns_api = [
    path("", include(router.urls)),
]

urlpatterns_web = [
    path("<str:tenant_slug>/", HomePageView.as_view(), name="core-home"),
    path("<str:tenant_slug>/page/<str:page_slug>/", PageView.as_view(), name="core-page"),
    path("<str:tenant_slug>/contact/", ContactPageView.as_view(), name="core-contact"),
    path("<str:tenant_slug>/contact/submit/", ContactSubmitView.as_view(), name="core-contact-submit"),
    path("<str:tenant_slug>/landing/", LandingPageView.as_view(), name="core-landing"),
    path("<str:tenant_slug>/coming-soon/", ComingSoonView.as_view(), name="core-coming-soon"),
]

urlpatterns = urlpatterns_api + urlpatterns_web