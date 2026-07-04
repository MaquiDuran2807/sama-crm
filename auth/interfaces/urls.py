"""Rutas REST de la app `auth`.

Expone los endpoints de autenticación y gestión de usuarios.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from auth.interfaces.views import (
    UserViewSet,
    LoginView,
    LogoutView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    user_permissions_view,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("permissions/", user_permissions_view, name="user-permissions"),
    path("", include(router.urls)),
]