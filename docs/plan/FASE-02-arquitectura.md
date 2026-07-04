# FASE 02: Arquitectura — Application Layer, Celery, Refactor

---

## Metadatos

| Campo | Valor |
|-------|-------|
| **ID** | FASE-02 |
| **Nombre** | Corrección de arquitectura hexagonal |
| **Prioridad** | 🟠 P1 — Alta |
| **Horas estimadas** | 8h |
| **Dependencias** | Fase 00 (para estructura de CI y documentación) |
| **Estado** | Pendiente |
| **Inicio planeado** | 2026-07-03 |

---

## Objetivo

Restaurar la integridad de la arquitectura hexagonal: implementar la capa `application/use_cases.py` faltante, migrar threading a Celery, y corregir el scheduler para que funcione en producción con múltiples workers.

---

## Reglas de Ejecución

1. **Documentación de cambios** → `docs/changelog/FASE-02-cambios.md`
2. **Tests obligatorios** para los nuevos casos de uso y tareas Celery
3. **No romper endpoints existentes**: los tests actuales deben seguir pasando
4. **Migración gradual**: threading y Celery pueden coexistir temporalmente
5. **Separación estricta de capas**: `application/` no puede importar de `interfaces/` ni `infrastructure/`
6. **Cada caso de uso nuevo debe estar documentado** con su propósito, inputs, outputs y errores

---

## Checklist de Tareas

### Tarea 02.1 — Implementar `crm/application/use_cases.py`
- [ ] Analizar qué vistas llaman a `domain.services` directamente
- [ ] Crear `CreateLeadUseCase`: orquesta creación de lead + LeadSource + validaciones
- [ ] Crear `ChangeLeadStageUseCase`: orquesta cambio de etapa, creación de actividad, reglas de etapa cerrada
- [ ] Crear `AddNoteUseCase`: orquesta agregar nota + actividad
- [ ] Crear `ReopenLeadUseCase`: orquesta reapertura + creación de recompra + actividades
- [ ] Crear `DeleteLeadUseCase`: orquesta soft-delete + registro
- [ ] Refactorizar las vistas para que llamen a casos de uso en vez de domain services directamente
- [ ] Mantener compatibilidad: las vistas deben seguir funcionando igual para el cliente

### Tarea 02.2 — Implementar `tenants/application/use_cases.py`
- [ ] Crear casos de uso para operaciones de tenant:
  - `GetTenantModulesUseCase`
  - `UpdatePipelineConfigUseCase`
  - `ValidateSubscriptionUseCase`

### Tarea 02.3 — Migrar threading a Celery (ingesta)
- [ ] Agregar configuración de Celery a `sama_core/celery.py`
- [ ] Instalar `celery` y `redis` en requirements
- [ ] Configurar Redis como broker en settings (`CELERY_BROKER_URL`)
- [ ] Migrar `ingesta/views.py::SyncTriggerView` a tarea Celery asíncrona
- [ ] Migrar `ingesta/views.py::SummaryTriggerView` a tarea Celery
- [ ] Migrar `ingesta/views.py::AudioBriefingTriggerView` a tarea Celery
- [ ] Mantener API de status polling funcional (ajustar para usar Celery result backend)
- [ ] Eliminar `SYNC_JOBS` global dict y `SYNC_JOBS_LOCK`

### Tarea 02.4 — Migrar scheduler a Celery Beat
- [ ] Configurar Celery Beat scheduler
- [ ] Migrar `ingesta/scheduler.py` a tarea periódica Celery Beat
- [ ] Migrar tareas existentes en `crm/infrastructure/tasks.py`:
  - `auto_advance_stale_leads` → Celery Beat cada 4h
  - `permanently_delete_old_leads` → Celery Beat diario
  - `send_task_reminders` → Celery Beat cada hora
- [ ] Eliminar APScheduler dependency (si ya no se usa)
- [ ] Eliminar `ingesta/scheduler.py` o dejarlo como fallback documentado

### Tarea 02.5 — Corregir `crm/infrastructure/tasks.py`
- [ ] `auto_advance_stale_leads`: corregir para iterar sobre todos los tenants activos
- [ ] `send_task_reminders`: implementar funcionalidad real (notificación en dashboard)
- [ ] Usar `transaction.atomic()` en `permanently_delete_old_leads`
- [ ] Agregar logging estructurado en todas las tareas

---

## Archivos Afectados

| Archivo | Acción | Riesgo |
|---------|--------|--------|
| `sama_core/celery.py` | Crear | **Alto** — configuración crítica |
| `sama_core/settings.py` | Modificar | Medio |
| `crm/application/use_cases.py` | Reescribir | **Alto** — arquitectura |
| `tenants/application/use_cases.py` | Reescribir | Medio |
| `crm/interfaces/views.py` | Modificar | **Alto** — refactor vistas para usar casos de uso |
| `crm/infrastructure/tasks.py` | Modificar | Medio |
| `ingesta/views.py` | Modificar | **Alto** — migrar threading a Celery |
| `ingesta/scheduler.py` | Modificar/Eliminar | Medio |
| `ingesta/services.py` | Modificar | Medio |
| `requirements.txt` | Modificar | Bajo |

---

## Criterios de Aceptación

1. ✅ Todos los ViewSets del CRM llaman a casos de uso (`application/`) en vez de domain services directamente
2. ✅ Las vistas REST siguen respondiendo exactamente igual (tests existentes pasan)
3. ✅ Celery está configurado y funcional
4. ✅ Async jobs en ingesta usan Celery (no threading)
5. ✅ Scheduler usa Celery Beat (no APScheduler en thread)
6. ✅ `SYNC_JOBS` global dict ha sido reemplazado por Celery result backend
7. ✅ Tareas programadas existentes están registradas en Celery Beat
8. ✅ `send_task_reminders` hace algo útil (no solo print)

---

## Tracking de Tiempo

| Fecha | Hora Ini | Hora Fin | Horas | Acumulado Fase | Acumulado Global | Tarea |
|-------|----------|----------|-------|----------------|------------------|-------|
| | | | | | | |

---

## Tracking de Líneas

| Archivo | Líneas Creadas | Líneas Eliminadas | Neto |
|---------|---------------|-------------------|------|
| | | | |
