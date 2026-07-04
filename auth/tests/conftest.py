"""Fixtures compartidas para tests de la app auth."""

import pytest
from rest_framework.test import APIClient
from auth.domain.models import User
from tenants.domain.models import Tenant


@pytest.fixture
def user_admin(db):
    return User.objects.create_user(
        username="admin",
        password="admin123",
        email="admin@sama.com",
        user_type=User.UserType.ADMIN,
        is_active=True,
    )


@pytest.fixture
def user_agent(db):
    return User.objects.create_user(
        username="agent",
        password="agent123",
        email="agent@sama.com",
        user_type=User.UserType.AGENT,
        is_active=True,
    )


@pytest.fixture
def user_viewer(db):
    return User.objects.create_user(
        username="viewer",
        password="viewer123",
        email="viewer@sama.com",
        user_type=User.UserType.VIEWER,
        is_active=True,
    )


@pytest.fixture
def user_inactive(db):
    return User.objects.create_user(
        username="inactive",
        password="inactive123",
        email="inactive@sama.com",
        user_type=User.UserType.AGENT,
        is_active=False,
    )


@pytest.fixture
def client_api(db):
    return APIClient()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(
        name="Auth Test Tenant",
        slug="auth-test",
        is_active=True,
    )
