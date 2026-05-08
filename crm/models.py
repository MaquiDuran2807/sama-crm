"""Puente de modelos de Django para la app `crm`.

Reexporta los modelos del dominio para que el ORM y el admin sigan la ruta
convencional `crm.models` mientras la estructura real permanece separada en la
capa de dominio.
"""

from crm.domain.models import *  # noqa: F401,F403
