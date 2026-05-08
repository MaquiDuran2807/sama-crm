"""Configuracion de la app Django `crm`.

Define el identificador interno que Django usa para registrar el modulo del
CRM dentro del proyecto principal.
"""

from django.apps import AppConfig


class CrmConfig(AppConfig):
    """Configuracion de la app `crm` en Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"
