"""Fixtures para tests de la app core."""

import pytest
from tenants.domain.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(
        name="Core Test Tenant",
        slug="core-test",
        is_active=True,
    )
