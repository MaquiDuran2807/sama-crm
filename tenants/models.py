"""Puente de modelos de Django para la app `tenants`.

Este modulo reexporta los modelos definidos en `tenants.domain.models` para
que el ORM de Django, el admin y las migraciones los detecten en la ruta
convencional `tenants.models` sin romper la estructura hexagonal.
"""

from tenants.domain.models import *  # noqa: F401,F403
