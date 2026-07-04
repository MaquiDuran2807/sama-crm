"""Configuración de la app Django `core`.

Define la clase de configuración que Django usa para registrar la aplicación
en `INSTALLED_APPS` y resolver correctamente su identidad interna.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuración de la app `core` en el registro de Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"