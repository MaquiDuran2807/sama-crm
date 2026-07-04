"""Tests para vistas de la app auth."""

import pytest
from rest_framework import status
from auth.domain.models import User


class TestLoginView:
    def test_login_success(self, db, client_api):
        User.objects.create_user(
            username="testuser", password="testpass123",
            user_type=User.UserType.AGENT,
        )
        response = client_api.post("/api/auth/login/", {
            "username": "testuser",
            "password": "testpass123",
        }, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_login_failure(self, db, client_api):
        response = client_api.post("/api/auth/login/", {
            "username": "nonexistent",
            "password": "wrong",
        }, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, db, client_api):
        User.objects.create_user(
            username="inactive", password="pass",
            is_active=False,
        )
        response = client_api.post("/api/auth/login/", {
            "username": "inactive",
            "password": "pass",
        }, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogoutView:
    def test_logout_authenticated(self, db, client_api, user_admin):
        client_api.force_authenticate(user=user_admin)
        response = client_api.post("/api/auth/logout/")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]


class TestUserViewSet:
    def test_me_endpoint(self, db, client_api, user_admin):
        client_api.force_authenticate(user=user_admin)
        response = client_api.get("/api/auth/users/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "admin"

    def test_me_requires_auth(self, db, client_api):
        response = client_api.get("/api/auth/users/me/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
