"""Configuración de la app Django `auth`.

Define la clase de configuración que Django usa para registrar la aplicación
en `INSTALLED_APPS` y resolver correctamente su identidad interna.
"""

from django.apps import AppConfig


class AuthConfig(AppConfig):
    """Configuración de la app `auth` en el registro de Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "auth"
    label = "local_auth"
    verbose_name = "SAMA Auth"