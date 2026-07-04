# FASE 05 — Cambios Realizados

| Tarea | Bug | Archivo | Cambio |
|-------|-----|---------|--------|
| 05.1 | B-01 | `crm/interfaces/views.py` | Eliminada primera definición duplicada de `CrmTrashTemplateView` (lines 678-708). Conservada la segunda (con csrf_token). |
| 05.2 | B-02 | `crm/domain/models.py` | `LeadQuerySet` movido antes de `LeadManager`. `LeadManager` cambiado a `models.Manager.from_queryset(LeadQuerySet)` para exponer `.active()`, `.deleted()`, `.closed()`. |
| 05.3 | B-03 | `crm/domain/services.py` | Agregado guard `if not lead.contact: return None` en `get_lead_summary()` antes de acceder a `phone_number`. |
| 05.4 | B-09 | `auth/templetes/` → `auth/templates/` | Directorio renombrado. `sama_core/settings.py` actualizado: `templetes` → `templates`. |
| 05.5 | — | Varios | Todos los imports en `crm/interfaces/views.py` están en uso. No hay nada que eliminar. |
| 05.6 | — | `crm/interfaces/views.py` | `_normalize_city_key`: `@lru_cache(maxsize=1)` → `@lru_cache(maxsize=128)` |
| 05.7 | — | Varios | No se encontraron bloques grandes de código comentado. |
| 05.8 | — | `scripts/` | Creado `scripts/__init__.py`. Los scripts `__` ya estaban en `scripts/`. |

## Tests

- `test_domain_services.py`: 30/30 pasaron
- `test_views.py`: 55/55 pasaron
