# Block 2 - Configuracion de Django Admin para tenants y crm

## Objetivo
Configurar Django Admin para las apps `tenants` y `crm` segun los requerimientos funcionales del bloque.

## Alcance
- Crear `tenants/admin.py` con:
  - `TenantAdmin` con `list_display`: name, tier, period, is_active, slug.
  - `list_filter` por tier e is_active.
  - inlines para `TenantModule` y `PipelineConfig`.
- Crear `crm/admin.py` con:
  - `LeadAdmin` con filtros por tenant, current_stage, is_closed.
  - inline de solo lectura para `LeadActivity`.
  - `ContactAdmin` con busqueda por phone_number y email.
- Agregar tests (pytest) para validar el registro/configuracion admin del bloque.

## Fuera de alcance
- Cambios en modelos de dominio.
- Implementacion de vistas, serializers, casos de uso o tareas.
- Ajustes de permisos avanzados del admin.

## Criterios de aceptacion
- Los modelos requeridos quedan registrados en Django admin.
- Las opciones solicitadas de `list_display`, `list_filter`, `search_fields` e inlines estan presentes.
- Existe test de verificacion para cada admin agregado.
