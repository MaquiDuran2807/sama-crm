# Cambios — FASE-03: Performance — N+1 Queries, Analytics, Optimización

**Fecha de ejecución:** 2026-07-03
**Horas estimadas:** 6h

---

## Resumen

Eliminación de N+1 queries críticos en LeadViewSet y ContactViewSet mediante
`prefetch_related`/`select_related`. Refactorización de `analytics_api` (~450
líneas → 6 helpers modulares) con consolidación de consultas temporales en una
sola query con `Case/When`. Cacheo de `get_lead_summary` (TTL 1h + invalidación
por señal), `computed_value` como `@cached_property`, y datos de analytics
timeline/regional (TTL 5 min). KPI targets agrupados por `period_type` para
reducir de O(N) a O(tipos). Ordenamiento de tareas movido de Python a SQL
(Case/When).

---

## Cambios Realizados

### [Refactor] `crm/interfaces/views.py`

#### Líneas 19-48 (imports)
- Añadido: `from django.core.cache import cache`
- Añadido: `from django.db.models.functions import TruncDate, TruncMonth`
- (Los helpers `_get_pipeline_stats`, `_get_source_stats`, `_get_timeline_stats`,
  `_get_regional_stats`, `_get_kpi_progress`, `_get_summary` ya existían en la
  refactor previa de FASE-03)

#### Lines 1239–1269: Cache en `analytics_api`
- **Qué cambió:** Timeline y regional se cachean con clave
  `analytics:{slug}:{days}:{offset}:{source}:timeline|regional` y TTL 300s.
- **Por qué:** Estos datos cambian poco (agregaciones históricas), evitar
  recomputarlos en cada request reduce queries.
- **Cómo funciona ahora:** Antes de llamar a `_get_timeline_stats` y
  `_get_regional_stats`, se consulta cache. Si miss, se computa y se almacena.

#### Lines 1–60: `get_queryset()` en LeadViewSet (Tarea 03.1)
- **Qué cambió:** Se añadió `prefetch_related("tasks", "lead_tags__tag")` y se
  cambió a `Prefetch("tasks", queryset=LeadTask.objects.filter(is_completed=False))`.
- **Por qué:** Evitar N+1 queries por lead al listar leads con tags y tareas.
  El filtro `is_completed=False` evita traer tareas completadas que no se
  muestran en el listado resumido.
- **Nota:** El Prefetch filtrado causó dos regresiones corregidas:
  1. `task_detail` pasó a usar `get_object_or_404(LeadTask, pk=..., lead=lead)`
     para bypasear la cache de prefetch.
  2. `LeadDetailSerializer.get_tasks` pasó a usar query directa
     `LeadTask.objects.filter(lead=obj)` para incluir tareas completadas.

#### Lines 60-80: `get_queryset()` en ContactViewSet (Tarea 03.2)
- **Qué cambió:** Se añadió `select_related("tenant", "referrer_contact")` y
  `prefetch_related(Prefetch("leads", queryset=Lead.objects.order_by("-created_at")))`.
- **Por qué:** El serializer `get_last_lead` accede a `leads.all()[0]` sin
  generar query extra.

#### Lines 850-971: Helpers de analytics (Tarea 03.3 y 03.4)
- **Qué cambió:** `_get_timeline_stats` usa una sola consulta con anotaciones
  `Case/When` para won, lost, quotes en lugar de 4 consultas separadas.
- **Por qué:** Reducir de 4 queries a 1.

#### Lines 975-1043: `_get_regional_stats`
- **Qué cambió:** Los datos geocodificados se iteran con `select_related` en
  lugar de N+1 queries por lead.

#### Lines 1046-1168: `_get_kpi_progress` (Tarea 03.7)
- **Qué cambió:** Se agrupan targets por `period_type` y se calculan métricas
  una vez por grupo. Se eliminó la iteración target por target que hacía
  O(N) consultas.
- **Por qué:** De O(N) a O(tipos_de_periodo). Con N=20 targets y 3 period_types,
  se pasa de 20 consultas a 3.

### [Refactor] `crm/interfaces/serializers.py`

#### `LeadSerializer.get_has_tasks`
- **Qué cambió:** Usa `bool(obj.tasks.all())` en lugar de `obj.tasks.count()`.
- **Por qué:** `all()` usa el prefetch cache; `count()` fuerza una query extra.

#### `ContactSerializer.get_last_lead`
- **Qué cambió:** Usa `obj.leads.all()[0]` en lugar de
  `obj.leads.order_by("-created_at").first()`.
- **Por qué:** `all()` usa el prefetch cache; `order_by().first()` fuerza una
  query extra.

#### `LeadDetailSerializer.get_tasks`
- **Qué cambió:** Usa `LeadTask.objects.filter(lead=obj).order_by("-created_at")`
  en lugar de `sorted(obj.tasks.all(), key=...)`.
- **Por qué:** El prefetch cache filtrado (`is_completed=False`) no incluye
  tareas completadas. El serializer detalle debe mostrar todas las tareas.

### [Refactor] `crm/interfaces/serializers.py` — Ordenamiento SQL (Tarea 03.3)
- **Qué cambió:** El ordenamiento de tareas por `due_date` y `created_at` se
  movió de Python (sorted()) a SQL (anotación `due_date_isnull` + `Case/When`
  en la vista de listado).
- **Por qué:** Evitar materialización en Python. La anotación `due_date_isnull`
  permite ordenar `NULL` last en SQL.

### [Optimización] `crm/domain/models.py` (Tarea 03.6)
#### Líneas 146-154: `computed_value`
- **Qué cambió:** De `@property` a `@cached_property` (de
  `django.utils.functional.cached_property`).
- **Por qué:** Evita repetir la query de `lead_products` en cada acceso.
- **Cómo funciona ahora:** El primer acceso computa el valor y lo cachea en
  `instance.__dict__`. Los siguientes accesos retornan el valor cacheado sin
  queries.

### [Feature] `crm/domain/services.py` (Tarea 03.5)
#### `get_lead_summary`
- **Qué cambió:** Se añadió cache con `cache.set(cache_key, result, 3600)`.
  La clave es `lead_summary_{lead.id}`.
- **Por qué:** El resumen IA rara vez cambia (DailyTextSummary se genera una
  vez al día). Cache con TTL 1h reduce queries repetitivas.

### [Feature] `crm/signals.py` (Nuevo archivo) (Tarea 03.5)
- **Qué cambió:** Señal `invalidate_lead_summary_cache` conectada a
  `post_save`/`post_delete` de `DailyTextSummary`.
- **Por qué:** Cuando se crea/actualiza un `DailyTextSummary`, se invalida el
  cache de `get_lead_summary` para asegurar frescura de datos.

### [Config] `sama_core/settings.py` (Tarea 03.5)
- **Qué cambió:** Se añadió `CACHES` con backend `LocMemCache` por defecto.
  Se puede cambiar a Redis vía variable de entorno `CACHE_BACKEND`.
- **Por qué:** Proporciona una cache funcional en desarrollo/tests sin
  dependencia de Redis.

### [Bugfix] `crm/interfaces/views.py` — `add_note`
- **Qué cambió:** Se removieron líneas unreachables después de `return`.
- **Por qué:** Código muerto.

### [Bugfix] `crm/interfaces/views.py` — `perform_update` (stage change)
- **Qué cambió:** Se pasa `old_stage` como parámetro explícito a
  `ChangeLeadStageUseCase.execute()`.
- **Por qué:** `serializer.save()` actualiza `lead.current_stage` antes de
  llamar al use case. El use case leía `lead.current_stage` (ya nuevo) y
  nunca detectaba el cambio (`old_stage == new_stage`), por lo que no
  registraba actividad ni cerraba el lead.

### [Bugfix] `crm/application/use_cases.py` — `ChangeLeadStageUseCase`
- **Qué cambió:** `execute()` ahora recibe `old_stage` como parámetro
  obligatorio y lo usa directamente en lugar de leer `lead.current_stage`.
- **Por qué:** Corregir bug donde el cambio de etapa no se detectaba.

### [Test Fix] `crm/tests/test_views.py`
- Añadido `TenantUser.objects.create()` en setUp de `CRMAPITestCase`,
  `TagAPITestCase` y `TaskAPITestCase` (faltaba para el filtrado multi-tenant).
- Añadido `?tenant_slug=codensolar` en `test_summary_endpoint_no_data`.
- Cambiado asset `crm/js/analytics.js` por `crm/js/shared/bridge.js` en
  `test_analytics_html_renders`.

---

## Tests Nuevos

### `crm/tests/test_views.py::PerformanceTestCase::test_lead_list_num_queries`
- **Qué prueba:** Listado de 10 leads con tags y tareas hace ≤5 queries.
- **Por qué:** Verificar que el Prefetch eliminó los N+1.
- **Cómo se ejecuta:** `python manage.py test crm.tests.test_views.PerformanceTestCase.test_lead_list_num_queries`

### `crm/tests/test_views.py::PerformanceTestCase::test_contact_list_num_queries`
- **Qué prueba:** Listado de contactos con leads prefetched hace ≤4 queries.
- **Por qué:** Verificar que `select_related` + `prefetch_related` eliminan N+1.

### `crm/tests/test_views.py::PerformanceTestCase::test_task_ordering_03_3`
- **Qué prueba:** El ordenamiento SQL produce el mismo resultado que el
  ordenamiento en Python.
- **Por qué:** Garantizar que el reemplazo de sorted() por Case/When es
  semánticamente equivalente.

### `crm/tests/test_views.py::PerformanceTestCase::test_analytics_api_num_queries`
- **Qué prueba:** Analytics API con datos hace <10 queries.
- **Por qué:** Criterio de aceptación: pasar de 30+ queries a <10.

### `crm/tests/test_views.py::PerformanceTestCase::test_lead_summary_cache`
- **Qué prueba:** Segunda llamada a `get_lead_summary` hace 0 queries (cache hit).
- **Por qué:** Verificar que el cache funciona correctamente.
- **Requiere:** `DailyTextSummary` y `ChatUser` en la BD.

### `crm/tests/test_views.py::PerformanceTestCase::test_computed_value_cached_property`
- **Qué prueba:** 10 accesos a `computed_value` hacen 1 sola query (productos).
- **Por qué:** Verificar que `@cached_property` cachea correctamente el valor.

---

## Decisiones de Diseño

- **Prefetch con QuerySet filtrado para tasks:** Se eligió `Prefetch` con
  `is_completed=False` para el listado de leads (LeadSerializer). Para el
  detalle (LeadDetailSerializer), se usa query directa para obtener todas las
  tareas. Alternativa considerada: prefetchear todas las tareas siempre, pero
  eso incrementa el volumen de datos innecesariamente en el listado.
- **Cache con TTL + invalidación por señal:** Se usa señal `post_save`/`post_delete`
  de `DailyTextSummary` para invalidar el cache de `get_lead_summary`. Esto
  permite un TTL largo (1h) sin riesgo de datos obsoletos. Alternativa
  considerada: solo TTL sin señal, descartada por posible stale data.
- **LocMemCache por defecto:** Permite tests sin Redis. En producción se
  configura Redis vía `CACHE_BACKEND` env var.

---

## Riesgos y Notas

- El Prefetch con QuerySet filtrado (`is_completed=False`) puede causar
  comportamientos inesperados si otro código accede a `lead.tasks` esperando
  todas las tareas. Se corrigieron las regresiones conocidas (task_detail,
  LeadDetailSerializer).
- `analytics_api` caching usa clave basada en `tenant_slug`, `days`, `offset`,
  `source_filter`. Si hay cambios en los datos subyacentes, el cache puede
  servir datos hasta 5 minutos obsoletos. Esto es aceptable para timeline y
  regional (datos históricos agregados que cambian poco).

---

## Tracking de Líneas

| Archivo | Creadas | Eliminadas | Neto |
|---------|---------|------------|------|
| `crm/interfaces/views.py` | +50 (helpers, cache) | -200 (código antiguo) | -150 |
| `crm/interfaces/serializers.py` | +10 | -5 | +5 |
| `crm/domain/models.py` | +1 (cached_property) | 0 | +1 |
| `crm/domain/services.py` | +8 (cache) | 0 | +8 |
| `crm/signals.py` | +15 (nuevo) | 0 | +15 |
| `crm/apps.py` | +3 (import signal) | 0 | +3 |
| `sama_core/settings.py` | +8 (CACHES) | 0 | +8 |
| `crm/tests/test_views.py` | +120 (tests) | -2 (fix) | +118 |
| **Total** | **+215** | **-207** | **+8** |
