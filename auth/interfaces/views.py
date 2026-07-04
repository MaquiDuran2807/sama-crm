"""Vistas de la app `auth`.

Este módulo contiene las vistas REST para autenticación, gestión de usuarios
y operaciones relacionadas con el portal SAMA.
"""

from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth.domain.services import (
    authenticate_user,
    create_password_reset_token,
    validate_password_reset_token,
    mark_token_as_used,
    check_user_permission,
    is_account_locked,
)
from auth.interfaces.serializers import (
    UserSerializer,
    UserCreateSerializer,
    LoginSerializer,
    LoginAttemptSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para usuarios del portal."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type == User.UserType.ADMIN:
            return User.objects.all()
        if user.tenant:
            return User.objects.filter(tenant=user.tenant)
        return User.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Retorna el usuario actual."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="change_password")
    def change_password(self, request):
        """Cambia la contraseña del usuario actual."""
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")
        new_password_confirm = request.data.get("new_password_confirm")

        if not all([current_password, new_password, new_password_confirm]):
            return Response({"detail": "Todos los campos son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != new_password_confirm:
            return Response({"detail": "Las contraseñas no coinciden"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(current_password):
            return Response({"detail": "Contraseña actual incorrecta"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Contraseña cambiada exitosamente"})


class LoginView(APIView):
    """Vista para autenticación de usuarios."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Autentica un usuario y retorna tokens de sesión."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        if is_account_locked(username):
            return Response(
                {"detail": "Cuenta bloqueada. Intenta más tarde."},
                status=status.HTTP_423_LOCKED,
            )

        ip_address = self.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

        user, message = authenticate_user(
            username=username,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if user is None:
            return Response({"detail": message}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            "user": UserSerializer(user).data,
            "message": message,
        })

    @staticmethod
    def get_client_ip(request):
        """Obtiene la IP del cliente."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class LogoutView(APIView):
    """Vista para cerrar sesión."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Cierra la sesión del usuario."""
        from django.contrib.auth import logout

        logout(request)
        return Response({"detail": "Sesión cerrada exitosamente"})


class PasswordResetRequestView(APIView):
    """Vista para solicitar reseteo de contraseña."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Envía email con token de recuperación."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Si el email existe, recibirás un enlace de recuperación"},
                status=status.HTTP_200_OK,
            )

        if user.is_active:
            token = create_password_reset_token(user)
            # TODO: Enviar email con el token
            # send_password_reset_email(user, token)

        return Response(
            {"detail": "Si el email existe, recibirás un enlace de recuperación"},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Vista para confirmar reseteo de contraseña."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Confirma el reseteo con el token y nueva contraseña."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        user = validate_password_reset_token(token)
        if user is None:
            return Response(
                {"detail": "Token inválido o expirado"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        mark_token_as_used(token)

        return Response({"detail": "Contraseña actualizada exitosamente"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_permissions_view(request):
    """Retorna los permisos del usuario actual."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    permissions = {
        "is_admin": request.user.user_type == User.UserType.ADMIN,
        "is_tenant_admin": request.user.user_type == User.UserType.TENANT_ADMIN,
        "is_agent": request.user.user_type == User.UserType.AGENT,
        "is_viewer": request.user.user_type == User.UserType.VIEWER,
        "tenant_id": request.user.tenant_id,
    }

    return Response(permissions)