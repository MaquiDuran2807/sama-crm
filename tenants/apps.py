"""Configuracion de la app Django `tenants`.

El archivo define la clase de configuracion que Django usa para registrar la
aplicacion en `INSTALLED_APPS` y resolver correctamente su identidad interna.
"""

from django.apps import AppConfig


class TenantsConfig(AppConfig):
    """Configuracion de la app `tenants` en el registro de Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tenants"
