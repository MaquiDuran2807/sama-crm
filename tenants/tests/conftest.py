"""Fixtures compartidas para tests de la app tenants."""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from tenants.domain.models import Tenant, PipelineConfig, TenantUser


User = get_user_model()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(
        name="Test Tenant",
        slug="testtenant",
        is_active=True,
        tier="basico",
    )


@pytest.fixture
def tenant_inactive(db):
    return Tenant.objects.create(
        name="Inactive Tenant",
        slug="inactive",
        is_active=False,
    )


@pytest.fixture
def pipeline(db, tenant):
    return PipelineConfig.objects.create(
        tenant=tenant,
        stages=[
            {"name": "Lead", "color": "#003366", "order": 1},
            {"name": "Cerrado Ganado", "color": "#00CC66", "order": 2, "is_closed": True},
        ],
        allow_skip_stages=True,
    )


@pytest.fixture
def user(db, tenant):
    u = User.objects.create_user(
        username="tenantadmin", password="testpass123",
        email="admin@tenant.com",
    )
    TenantUser.objects.create(user=u, tenant=tenant)
    return u


@pytest.fixture
def client_api(db, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client
