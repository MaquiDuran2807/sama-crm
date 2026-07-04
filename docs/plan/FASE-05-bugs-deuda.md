# FASE 05: Bugs y Deuda Técnica

---

## Metadatos

| Campo | Valor |
|-------|-------|
| **ID** | FASE-05 |
| **Nombre** | Corrección de bugs y limpieza |
| **Prioridad** | 🟡 P2 — Media |
| **Horas estimadas** | 4h |
| **Dependencias** | Fase 01 (seguridad) — para evitar conflictos en views.py |
| **Estado** | Pendiente |
| **Inicio planeado** | 2026-07-05 |

---

## Objetivo

Corregir los bugs conocidos (B-01 a B-10), eliminar dead code, y limpiar la deuda técnica que no requiere cambios arquitectónicos mayores.

---

## Reglas de Ejecución

1. **Documentación de cambios** → `docs/changelog/FASE-05-cambios.md`
2. **Tests para cada bug**: demostrar que el bug existía y que el fix lo resuelve
3. **No cambiar comportamiento**: solo corregir lo que está mal, no refactorizar
4. **Atomicidad**: un commit por bug corregido

---

## Checklist de Tareas

### Tarea 05.1 — Eliminar `CrmTrashTemplateView` duplicada (B-01)
- [ ] Identificar las dos definiciones en `crm/interfaces/views.py` (líneas 664 y 706)
- [ ] Conservar la segunda (completa, con csrf_token)
- [ ] Eliminar la primera definición
- [ ] Verificar que la ruta siga funcionando (tests de trash page)
- [ ] Test: trash page renderiza con csrf_token

### Tarea 05.2 — Corregir `LeadQuerySet` (B-02)
- [ ] Cambiar `LeadManager` a: `LeadManager(models.Manager.from_queryset(LeadQuerySet))`
- [ ] Verificar que `Lead.objects.active()` funciona
- [ ] Verificar que `Lead.objects.deleted()` funciona
- [ ] Verificar que `Lead.objects.closed()` funciona
- [ ] Refactorizar consultas existentes que podrían usar estos métodos
- [ ] Test: cada método QuerySet devuelve los leads correctos

### Tarea 05.3 — Fix `get_lead_summary()` crash (B-03)
- [ ] Agregar `if not lead.contact: return None` antes de acceder a `phone_number`
- [ ] Agregar `select_related("contact")` en la consulta
- [ ] Test: lead sin contacto no crashea, retorna None

### Tarea 05.4 — Fix typo `templetes/` → `templates/` (B-09)
- [ ] Renombrar carpeta `auth/templetes/` a `auth/templates/`
- [ ] Actualizar `TEMPLATES[0]['DIRS']` en `sama_core/settings.py`
- [ ] Verificar que los templates de auth se cargan correctamente
- [ ] Verificar que no hay otras referencias a `templetes/` en el código

### Tarea 05.5 — Eliminar imports muertos
- [ ] Eliminar `import unicodedata` de `crm/interfaces/views.py`
- [ ] Eliminar `from collections import defaultdict`
- [ ] Eliminar `from functools import lru_cache`
- [ ] Eliminar `from pathlib import Path`
- [ ] Verificar que no se usan en ninguna función
- [ ] Buscar otros imports muertos en todo el proyecto (con `vulture` o manual)

### Tarea 05.6 — Corregir `_normalize_city_key` (lru_cache mal usado)
- [ ] Reemplazar `@lru_cache(maxsize=1)` por cache más amplio o eliminarlo si no es necesario
- [ ] Si la función es pura y se llama con muchas ciudades, usar `maxsize=128`
- [ ] Si solo se llama una vez por request, eliminar cache

### Tarea 05.7 — Eliminar código comentado
- [ ] Buscar bloques grandes de código comentado en `crm/interfaces/views.py`
- [ ] Buscar en `crm/domain/services.py`
- [ ] Eliminar bloques comentados (si son importantes, mover a docs/tickets)

### Tarea 05.8 — Renombrar scripts en raíz
- [ ] si no se hizo en Fase 00, mover scripts `__` a `scripts/`
- [ ] Agregar `scripts/__init__.py`
- [ ] Verificar que `manage.py` no depende de ningún script en raíz

---

## Archivos Afectados

| Archivo | Acción | Riesgo |
|---------|--------|--------|
| `crm/interfaces/views.py` | Modificar | **Alto** — múltiples cambios |
| `crm/domain/models.py` | Modificar | Medio |
| `crm/domain/services.py` | Modificar | Medio |
| `auth/templetes/` → `auth/templates/` | Renombrar | **Alto** — puede romper templates |
| `sama_core/settings.py` | Modificar | Bajo |
| Varios | Eliminar imports | Bajo |

---

## Criterios de Aceptación

1. ✅ No hay `CrmTrashTemplateView` duplicada
2. ✅ `Lead.objects.active()`, `deleted()`, `closed()` funcionan
3. ✅ `get_lead_summary()` no crashea con lead sin contacto
4. ✅ Carpeta `auth/` se llama `templates/` (no `templetes/`)
5. ✅ No hay imports de módulos que no se usan
6. ✅ `_normalize_city_key` tiene cache sensible
7. ✅ No hay bloques grandes de código comentado
8. ✅ La raíz del proyecto no tiene scripts `__`
9. ✅ Todos los tests existentes pasan

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
