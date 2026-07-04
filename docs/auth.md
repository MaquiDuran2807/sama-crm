# Auth

## Objetivo
El módulo `auth` centraliza la autenticación y la gestión de usuarios del portal SAMA dentro de la arquitectura hexagonal existente.

## Componentes
- `auth/domain/`: modelo `User`, `LoginAttempt` y `PasswordResetToken`.
- `auth/interfaces/`: vistas y serializers REST para login, logout, permisos y gestión de usuarios.
- `auth/admin.py`: administración de usuarios y trazabilidad de acceso.

## Rutas relevantes
- Web login: `/accounts/login/`
- Web logout: `/accounts/logout/`
- API auth: `/api/auth/`
- Home público: `/`

## Notas
- El modelo custom se expone como `local_auth.User`.
- El logout del dashboard debe hacer `POST` hacia la ruta web de logout.
- Después de cerrar sesión, el usuario vuelve al home público.
