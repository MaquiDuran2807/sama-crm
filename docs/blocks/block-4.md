# Block 4 - Dashboard web para la app crm

## Objetivo
Exponer el dashboard visual de CRM desde la propia app `crm`, usando la plantilla existente en `crm/templates/crm/dashboard.html`.

## Alcance
- Crear rutas web para el dashboard y el detalle de lead dentro del dominio `crm`.
- Crear vistas HTML que carguen la plantilla `crm/dashboard.html` y un detalle basico de lead.
- Reutilizar la logica de dominio existente para pipeline, estadisticas y resumen IA.
- Agregar pruebas de vistas para validar que las paginas HTML respondan correctamente.

## Fuera de alcance
- Redisenar el dashboard o su CSS/JS.
- Cambiar la API REST existente de contactos y leads.
- Migrar el dashboard de `ingesta`.

## Criterios de aceptacion
- El dashboard de CRM responde en una URL propia de `crm`.
- Los enlaces de leads del dashboard apuntan a una vista funcional.
- Existen tests que confirman el renderizado de las paginas HTML.
