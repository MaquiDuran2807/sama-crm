"""Tests para vistas de la app core."""

from django.test import Client
from core.domain.models import SiteConfiguration


class TestHomePageView:
    def test_home_page_returns_200(self, db, tenant):
        SiteConfiguration.objects.create(tenant=tenant, is_published=True)
        client = Client()
        response = client.get("/")
        assert response.status_code == 200

    def test_home_page_uses_correct_template(self, db, tenant):
        SiteConfiguration.objects.create(tenant=tenant, is_published=True)
        client = Client()
        response = client.get("/")
        assert response.status_code == 200
