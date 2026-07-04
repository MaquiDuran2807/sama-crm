"""Fixtures compartidas para tests de la app CRM."""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from tenants.domain.models import Tenant, PipelineConfig, TenantUser
from crm.domain.models import Contact, Lead, Product, Tag


User = get_user_model()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(
        name="Test Tenant",
        slug="testtenant",
        is_active=True,
    )


@pytest.fixture
def pipeline(db, tenant):
    return PipelineConfig.objects.create(
        tenant=tenant,
        stages=[
            {"name": "Lead", "color": "#003366", "order": 1},
            {"name": "Calificacion", "color": "#FF9933", "order": 2, "skip_allowed": True},
            {"name": "Propuesta", "color": "#3366FF", "order": 3},
            {"name": "Negociacion", "color": "#FF33CC", "order": 4},
            {"name": "Cerrado Ganado", "color": "#00CC66", "order": 5, "is_closed": True},
            {"name": "Cerrado Perdido", "color": "#CC0000", "order": 6, "is_closed": True},
        ],
        allow_skip_stages=True,
    )


@pytest.fixture
def user(db, tenant):
    u = User.objects.create_user(
        username="testuser", password="testpass123",
        email="test@example.com",
    )
    TenantUser.objects.create(user=u, tenant=tenant)
    return u


@pytest.fixture
def contact(db, tenant):
    return Contact.objects.create(
        tenant=tenant,
        full_name="Juan Perez",
        phone_number="573001234567",
    )


@pytest.fixture
def contact2(db, tenant):
    return Contact.objects.create(
        tenant=tenant,
        full_name="Maria Gomez",
        phone_number="573007654321",
    )


@pytest.fixture
def lead_in_lead(db, tenant, contact, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Lead",
        is_closed=False,
    )


@pytest.fixture
def lead_in_calificacion(db, tenant, contact, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Calificacion",
        is_closed=False,
    )


@pytest.fixture
def lead_closed_won(db, tenant, contact, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Cerrado Ganado",
        is_closed=True,
        closed_result="won",
    )


@pytest.fixture
def lead_closed_lost(db, tenant, contact2, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact2,
        current_stage="Cerrado Perdido",
        is_closed=True,
        closed_result="lost",
    )


@pytest.fixture
def client_api(db, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def tag(db, tenant):
    return Tag.objects.create(tenant=tenant, name="VIP", color="#FFD700")


@pytest.fixture
def product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="Panel Solar 450W",
        sku="PS-450",
        price=1500000,
        is_active=True,
    )
