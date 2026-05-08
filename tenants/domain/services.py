"""Servicios de dominio para la app tenants.

Este modulo agrupa la logica de negocio pura relacionada con la suscripcion
del cliente, el pipeline comercial y los campos personalizados. Las funciones
expuestas aqui son consumidas por la capa de interfaces y por otros casos de
uso internos, pero no conocen detalles de HTTP, formularios ni tareas externas.
"""

from __future__ import annotations

from datetime import date

from django.db.models import QuerySet
from django.utils import timezone

from tenants.domain.models import CustomField, Tenant, TenantModule


def is_subscription_active(tenant: Tenant) -> bool:
	"""Indica si la suscripcion del tenant esta vigente en la fecha actual.

	Args:
		tenant: Instancia de tenant que se evaluara.

	Returns:
		``True`` cuando la fecha actual cae dentro del rango definido por
		``subscription_start`` y ``subscription_end`` y el tenant esta activo.
	"""

	if not tenant.is_active:
		return False
	today = timezone.localdate()
	if tenant.subscription_start and today < tenant.subscription_start:
		return False
	if tenant.subscription_end and today > tenant.subscription_end:
		return False
	return True


def get_pipeline_stages(tenant: Tenant) -> list[dict[str, object]]:
	"""Retorna las etapas del pipeline definidas para el tenant.

	Args:
		tenant: Tenant propietario de la configuracion del pipeline.

	Returns:
		Lista de diccionarios ordenada por el campo ``order``.
	"""

	pipeline_config = getattr(tenant, "pipeline_config", None)
	if pipeline_config is None:
		return []
	return sorted(list(pipeline_config.stages or []), key=lambda stage: stage.get("order", 0))


def get_active_modules(tenant: Tenant) -> QuerySet[TenantModule]:
	"""Obtiene los modulos activos del tenant.

	Args:
		tenant: Tenant sobre el que se consulta la lista de modulos activos.

	Returns:
		QuerySet de `TenantModule` filtrado por ``is_active=True``.
	"""

	return TenantModule.objects.filter(tenant=tenant, is_active=True).order_by("module_key")


def get_custom_fields(tenant: Tenant, target_model: str) -> QuerySet[CustomField]:
	"""Obtiene los campos personalizados del tenant para un modelo objetivo.

	Args:
		tenant: Tenant propietario de los campos.
		target_model: Valor del enum de destino (``contact`` o ``lead``).

	Returns:
		QuerySet de `CustomField` filtrado y ordenado por el campo ``order``.
	"""

	return CustomField.objects.filter(tenant=tenant, target_model=target_model).order_by("order", "field_name")
