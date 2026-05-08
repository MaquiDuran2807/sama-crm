# Block 3 - Management command seed_solar_client

## Objetivo
Crear el comando de management `seed_solar_client` en la app `crm` para sembrar datos base del cliente solar Codensolar.

## Alcance
- Crear `Tenant` Codensolar SAS con slug `codensolar`, tier `pro` y suscripcion trimestral activa.
- Crear o actualizar `PipelineConfig` con 6 etapas y colores definidos.
- Crear 3 `CustomField`: `tipo_cliente`, `consumo_kwh`, `fecha_instalacion`.
- Crear 5 `Contact` con datos realistas.
- Crear 8 `Lead` distribuidos en distintas etapas.
- Crear 3 `DailyTextSummary` asociados a `ChatUser` de algunos contactos.
- Imprimir resumen final de elementos creados/actualizados.

## Fuera de alcance
- Exponer endpoint API para el seeding.
- Poblar mensajes o interacciones historicas de `ingesta`.

## Criterios de aceptacion
- El comando `python manage.py seed_solar_client` ejecuta sin errores.
- Se insertan o actualizan los registros solicitados.
- Se muestra en consola un resumen de lo creado/actualizado.
- Existe test pytest para validar el comportamiento principal del comando.
