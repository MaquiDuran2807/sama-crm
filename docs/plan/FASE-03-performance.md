# FASE 03: Performance — N+1 Queries, Analytics, Optimización

---

## Metadatos

| Campo | Valor |
|-------|-------|
| **ID** | FASE-03 |
| **Nombre** | Optimización de performance |
| **Prioridad** | 🟠 P1 — Alta |
| **Horas estimadas** | 6h |
| **Dependencias** | Fase 01 (seguridad) — para evitar conflictos en views.py |
| **Estado** | Pendiente |
| **Inicio planeado** | 2026-07-03 |

---

## Objetivo

Eliminar los N+1 queries críticos, reducir consultas de analytics de 30+ a ~5, y optimizar el pipeline de datos del dashboard para que sea rápido con 1000+ leads.

---

## Reglas de Ejecución

1. **Documentación de cambios** → `docs/changelog/FASE-03-cambios.md`
2. **Tests obligatorios**: verificar que las queries se redujeron (assertNumQueries)
3. **No cambiar comportamiento**: las APIs deben devolver exactamente los mismos datos
4. **Medir antes y después**: registrar el número de queries antes y después de cada cambio
5. **Atomicidad**: cada endpoint optimizado es un commit separado

---

## Checklist de Tareas

### Tarea 03.1 — Optimizar `LeadViewSet.get_queryset()` (P-01)
- [ ] Agregar `prefetch_related("tasks", "lead_tags__tag")` ANTES de aplicar filtros
- [ ] Usar `Prefetch` con QuerySet filtrado para tasks (solo no completadas)
- [ ] Verificar que filtros `has_tasks` y `tag` no duplican prefetch
- [ ] Test con `assertNumQueries` para un listado de 10 leads con tags y tareas

### Tarea 03.2 — Optimizar `ContactViewSet.get_queryset()` (P-02)
- [ ] Agregar `select_related("tenant", "referrer_contact")`
- [ ] Agregar `prefetch_related("leads")` si se usan en serializers
- [ ] Test con `assertNumQueries`

### Tarea 03.3 — Optimizar ordenamiento de tareas (P-03)
- [ ] Reemplazar ordenamiento en Python por anotaciones SQL (`Case/When`)
- [ ] Eliminar `list(tasks_qs)` materialización en Python
- [ ] Test: verificar que el orden es el mismo antes y después

### Tarea 03.4 — Refactorizar `analytics_api()` (P-04)
- [ ] Dividir la función monstruo (~450 líneas) en módulos separados:
  - `get_pipeline_stats()` — conteos por etapa
  - `get_source_stats()` — distribución por fuente
  - `get_regional_stats()` — datos por departamento/ciudad
  - `get_timeline_stats()` — tendencias temporales
  - `get_kpi_progress()` — avance de metas
- [ ] Reducir queries: usar una sola consulta con anotaciones agregadas en vez de count() separados
- [ ] Agregar cache (`@cache_page` o `django.core.cache`) para datos que cambian poco (timeline, regional)
- [ ] Test con `assertNumQueries`: debe pasar de 30+ a <10

### Tarea 03.5 — Cachear `get_lead_summary()` (P-06)
- [ ] Aggregar `select_related("contact")` o verificar que `contact` no es None
- [ ] Agregar cache a nivel de aplicación (django cache, TTL 1 hora)
- [ ] Invalidar cache cuando se crea/actualiza un DailyTextSummary
- [ ] Test: primera llamada va a BD, segunda llamada usa cache

### Tarea 03.6 — Cachear `computed_value` en Lead (B-04)
- [ ] Cachear a nivel de instancia de Python (`@cached_property` o atributo `_computed_value`)
- [ ] O convertir a anotación SQL en `get_queryset()` con `Subquery`/`Sum`
- [ ] Test: verificar que acceder 10 veces a `computed_value` hace 1 query no 10

### Tarea 03.7 — KPI targets: optimizar loop anidado (P-05)
- [ ] Reemplazar loop de targets con queries agregadas (una sola consulta)
- [ ] Calcular targets en lote, no uno por uno

---

## Archivos Afectados

| Archivo | Acción | Riesgo |
|---------|--------|--------|
| `crm/interfaces/views.py` | Modificar | **Alto** — LeadViewSet, ContactViewSet, analytics_api |
| `crm/domain/services.py` | Modificar | Medio |
| `crm/domain/models.py` | Modificar | Bajo (computed_value) |
| `crm/interfaces/serializers.py` | Modificar | Bajo |

---

## Criterios de Aceptación

1. ✅ Listado de leads con 10 elementos hace <10 queries (antes: 20+)
2. ✅ Listado de contactos con `select_related` (antes: N+1)
3. ✅ `analytics_api()` hace <10 queries (antes: 30+)
4. ✅ Ordenamiento de tareas usa SQL, no Python
5. ✅ `computed_value` no genera queries extras en loop
6. ✅ `get_lead_summary()` usa cache
7. ✅ Todos los tests existentes siguen pasando

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
