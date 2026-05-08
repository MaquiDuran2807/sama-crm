# Block 1 - Scaffolding hexagonal base para tenants y crm

## Objetivo
Crear la estructura inicial de arquitectura hexagonal para las apps `tenants` y `crm` segun SDD, sin implementar logica de negocio ni modelos.

## Alcance
- Crear app folders y capas:
  - domain/
  - application/
  - interfaces/
  - infrastructure/
- Crear archivos base por capa.
- Dejar `domain/models.py` vacio en ambas apps para que el usuario pegue los modelos.
- Agregar comentarios de proposito en todos los demas archivos creados.

## Fuera de alcance
- Implementacion de modelos, servicios, casos de uso, serializers, views, rutas funcionales o tareas Celery reales.
- Migraciones.
- Integracion con otras apps.

## Entregables
- Estructura de carpetas y archivos para `tenants`.
- Estructura de carpetas y archivos para `crm`.

## Criterios de aceptacion
- Existen todas las carpetas y archivos solicitados.
- `domain/models.py` en ambas apps esta vacio.
- Todos los otros archivos tienen comentario de proposito de capa.
