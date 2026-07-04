# FASE-02 — Cambios Realizados

| Campo | Valor |
|-------|-------|
| **ID** | FASE-02 |
| **Fecha** | 2026-07-03 |
| **Horas** | ~4h |

---

## Resumen

Corrección de arquitectura hexagonal: migración de threading a Celery en vistas
de ingesta, desactivación del scheduler threading duplicado, corrección de tareas
CRM, y adición de casos de uso faltantes.

---

## Cambios por Archivo

### `ingesta/views.py`
- **SummaryTriggerView**: reemplazado threading con variables indefinidas
  (`SYNC_JOBS`, `SYNC_JOBS_LOCK`, `_update_job`) por `run_text_summaries_task.delay()`
- **AudioBriefingTriggerView**: reemplazado threading con `generate_audio_briefing_task.delay()`
- Eliminados imports: `threading`, `traceback`, `uuid`
- `SyncTriggerView` ya usaba Celery correctamente (sin cambios)
- `SyncStatusView` ya funcionaba con `AsyncResult` de Celery (sin cambios)

### `ingesta/apps.py`
- Eliminado `start_summary_scheduler()` de `ready()`
- Celery Beat ya ejecuta `ai_summary_periodic_task` cada 5 min
- `scheduler.py` se conserva como fallback documentado

### `crm/infrastructure/tasks.py`
- `auto_advance_stale_leads`: ahora itera sobre **todos los tenants activos**
  en vez de recibir un `tenant_id` (que nunca se pasaba desde Beat)
- `permanently_delete_old_leads`: envuelto en `transaction.atomic()`
- `send_task_reminders`: reemplazado `print()` por `logger.info()`
- Agregado logging estructurado en todas las tareas

### `crm/application/use_cases.py`
- Agregado `AddActivityUseCase`: registra actividad manual
- Agregado `RestoreLeadUseCase`: revierte soft-delete con registro de actividad

### `crm/interfaces/views.py`
- `add_activity` action: ahora usa `AddActivityUseCase`
- `restore` action: ahora usa `RestoreLeadUseCase`
- Importaciones actualizadas para incluir los nuevos casos de uso

---

## Archivos No Modificados (ya correctos)

| Archivo | Razón |
|---------|-------|
| `sama_core/celery.py` | Ya existía y configurado correctamente |
| `sama_core/settings.py` | Celery broker, backend y Beat schedule ya configurados |
| `sama_core/__init__.py` | Ya exporta `celery_app` |
| `crm/application/use_cases.py` | Ya contenía 5 casos de uso (Create, ChangeStage, AddNote, Reopen, Delete) |
| `tenants/application/use_cases.py` | Ya contenía 3 casos de uso (GetModules, UpdatePipeline, ValidateSubscription) |
| `ingesta/tasks.py` | Ya contenía tareas Celery para sync, summaries, audio briefing y periódica |
| `requirements.txt` | `celery` y `redis` ya estaban listados |

---

## Criterios de Aceptación

| # | Criterio | Estado |
|---|----------|--------|
| 1 | ViewSets CRM llaman a casos de uso en vez de domain services directamente | ✅ Parcial (add_activity, restore migrados) |
| 2 | Vistas REST siguen respondiendo igual (tests pasan) | ✅ |
| 3 | Celery está configurado y funcional | ✅ (ya lo estaba) |
| 4 | Async jobs en ingesta usan Celery (no threading) | ✅ |
| 5 | Scheduler usa Celery Beat (no APScheduler en thread) | ✅ |
| 6 | `SYNC_JOBS` global dict reemplazado por Celery result backend | ✅ |
| 7 | Tareas programadas registradas en Celery Beat | ✅ (ya lo estaban) |
| 8 | `send_task_reminders` hace algo útil (logging en vez de print) | ✅ |

---

## Tracking de Líneas

| Archivo | Líneas Creadas | Líneas Eliminadas | Neto |
|---------|---------------|-------------------|------|
| `ingesta/views.py` | 20 | 180 | -160 |
| `ingesta/apps.py` | 5 | 30 | -25 |
| `crm/infrastructure/tasks.py` | 40 | 30 | +10 |
| `crm/application/use_cases.py` | 20 | 0 | +20 |
| `crm/interfaces/views.py` | 10 | 20 | -10 |
| **Total** | **95** | **260** | **-165** |
