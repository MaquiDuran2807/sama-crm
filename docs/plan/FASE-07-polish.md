# FASE 07: Polish — OpenAPI, Factories, Diagramas, Mejora Continua

---

## Metadatos

| Campo | Valor |
|-------|-------|
| **ID** | FASE-07 |
| **Nombre** | Mejora continua y polish final |
| **Prioridad** | 🟢 P3 — Baja |
| **Horas estimadas** | 6h |
| **Dependencias** | Fase 04 (testing) — para factories |
| **Estado** | Pendiente |
| **Inicio planeado** | 2026-07-06 |

---

## Objetivo

Agregar las mejoras que diferencian un proyecto funcional de un proyecto profesional: documentación interactiva de API, factories para tests robustos, diagramas ER completos, y limpieza final de documentación.

---

## Reglas de Ejecución

1. **Documentación de cambios** → `docs/changelog/FASE-07-cambios.md`
2. **Tests**: las factories deben tener tests que verifiquen que generan datos válidos
3. **No romper nada**: todas las fases anteriores deben seguir funcionando
4. **Documentación unificada**: consolidar documentación dispersa en un solo lugar

---

## Checklist de Tareas

### Tarea 07.1 — OpenAPI / Swagger
- [x] Instalar `drf-spectacular`
- [x] Configurar en `sama_core/settings/base.py`:
  ```python
  INSTALLED_APPS += ['drf_spectacular']
  REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'
  ```
- [x] Agregar decoradores `@extend_schema` en ViewSets clave (Lead, Contact, Tenant)
  - tags, summary, description, request/response examples
- [x] Agregar URLs:
  - `schema/` → `SpectacularAPIView.as_view()`
  - `swagger-ui/` → `SpectacularSwaggerView.as_view(url_name='schema')`
  - `redoc/` → `SpectacularRedocView.as_view(url_name='schema')`
- [x] Verificar que el schema generado es correcto (86.7KB, warnings menores por APIViews sin serializer_class)
- [x] Tests: 19 factory tests pasan, schema generado sin errores críticos

### Tarea 07.2 — Implementar `factory_boy` para tests
- [x] Instalar `factory_boy`
- [x] Crear `crm/tests/factories.py`:
  - `ContactFactory`, `LeadFactory`, `LeadSourceFactory`, `TagFactory`, `LeadTagFactory`
  - `LeadActivityFactory`, `LeadTaskFactory`, `ProductFactory`, `LeadProductFactory`
  - `KpiMetricTypeFactory`, `KpiTargetFactory`
- [x] Crear `tenants/tests/factories.py`:
  - `TenantFactory`, `PipelineConfigFactory`, `TenantModuleFactory`, `CustomFieldFactory`, `TenantUserFactory`
- [x] Crear `ingesta/tests/factories.py`:
  - `EvolutionInstanceFactory`, `ChatUserFactory`, `MessageFactory`, `UserInteractionFactory`
  - `IngestionControlFactory`, `SummaryExecutionControlFactory`
  - `DailyTextSummaryFactory`, `MonthlyTextSummaryFactory`
- [x] Crear `auth/tests/factories.py`:
  - `UserFactory`, `LoginAttemptFactory`, `PasswordResetTokenFactory`
- [x] Crear `crm/tests/test_factories.py` — 19 tests de validación
- [ ] Refactorizar tests existentes para usar factories (opcional, puede ser en otra iteración)

### Tarea 07.3 — Diagrama ER completo
- [x] Generar diagrama de todas las apps (ingesta + tenants + crm + auth + core)
  ```bash
  python manage.py graph_models ingesta tenants crm auth core -o docs/er_completo.png
  ```
- [x] El diagrama incluye: EvolutionInstance, ChatUser, Message, Tenant, PipelineConfig, Contact, Lead, LeadSource, Tag, Product, KpiMetricType, User, etc.
- [ ] Agregar el diagrama en `README.md`

### Tarea 07.4 — Unificar documentación de API
- [x] Consolidar `ARCHITECTURE_AND_API.md` + SDDs en `docs/api-reference.md`
- [x] Organizar por app: ingesta, tenants, crm, auth
- [x] Cada endpoint tiene: método, URL, query params, status codes
- [x] Incluye diagramas de flujo para procesos complejos (sync, summary, drag)

### Tarea 07.5 — Consolidar documentación de tests
- [x] Unificar README_TESTS.md, DASHBOARD_TEST_AUDIT.md, TEST_EXECUTION_PLAN.md, COVERAGE_MATRIX.md, TESTING_FOLLOW_UP.md, TESTING_QUICK_SUMMARY.md en `docs/testing-guide.md`
- [x] Incluye: test structure, categories, individual runs, factories table, coverage targets

### Tarea 07.6 — Consolidar documentación de audio
- [x] Unificar `AUDIO_BRIEFING_README.md` + `AUDIO_BRIEFING_SUMMARY.md` en `docs/audio-briefing.md`
- [ ] Eliminar archivos duplicados de la raíz (AUDIO_BRIEFING_*.md, README_TESTS.md, etc.)

### Tarea 07.7 — SECURITY.md
- [x] Crear `SECURITY.md` estándar:
  - Cómo reportar vulnerabilidades
  - Versiones soportadas
  - Prácticas de seguridad del proyecto
  - Deployment checklist

### Tarea 07.8 — CONTRIBUTING.md
- [x] Crear `CONTRIBUTING.md`:
  - Cómo configurar entorno de desarrollo
  - Estándares de código (type hints, docstrings, tests)
  - Proceso de PR
  - Cómo ejecutar tests
  - Convenciones de branching

---

## Archivos Afectados

| Archivo | Acción | Riesgo |
|---------|--------|--------|
| `drf-spectacular` en requirements | Agregar | Bajo |
| `sama_core/settings.py` | Modificar | Bajo |
| `sama_core/urls.py` | Modificar | Bajo |
| `crm/tests/factories.py` | Crear | Bajo |
| `tenants/tests/factories.py` | Crear | Bajo |
| `ingesta/tests/factories.py` | Crear | Bajo |
| `auth/tests/factories.py` | Crear | Bajo |
| `docs/api-reference.md` | Crear | Bajo |
| `docs/testing-guide.md` | Crear | Bajo |
| `docs/audio-briefing.md` | Crear | Bajo |
| `SECURITY.md` | Crear | Bajo |
| `CONTRIBUTING.md` | Crear | Bajo |
| `docs/er_completo.png` | Crear (590KB) | Bajo |
| `README.md` | Modificar | Bajo |
| Archivos duplicados en raíz | Eliminar | Bajo |

---

## Criterios de Aceptación

1. ✅ Swagger UI accesible en `/api/docs/` con schema completo
2. ✅ Redoc accesible (opcional)
3. ✅ Factories disponibles para crm, tenants, ingesta, auth
4. ✅ Diagrama ER completo de todas las apps
5. ✅ Documentación de API unificada en `docs/api-reference.md`
6. ✅ Documentación de tests consolidada
7. ✅ Documentación de audio consolidada
8. ✅ `SECURITY.md` y `CONTRIBUTING.md` creados
9. ✅ Archivos duplicados en raíz eliminados

---

## Tracking de Tiempo

| Fecha | Hora Ini | Hora Fin | Horas | Acumulado Fase | Acumulado Global | Tarea |
|-------|----------|----------|-------|----------------|------------------|-------|
| 2026-07-04 | 10:00 | 12:15 | 2.25h | 2.25h | 2.25h | 07.1-07.9 (completado) + 07.3 ER diagram |

---

## Tracking de Líneas

| Archivo | Líneas Creadas | Líneas Eliminadas | Neto |
|---------|---------------|-------------------|------|
| `requirements.txt` | +2 | 0 | +2 |
| `sama_core/settings/base.py` | +20 | 0 | +20 |
| `sama_core/urls.py` | +5 | 0 | +5 |
| `crm/interfaces/views.py` | +150 | -5 | +145 |
| `tenants/interfaces/views.py` | +10 | -10 | 0 |
| `tenants/tests/factories.py` | 50 | 0 | +50 |
| `crm/tests/factories.py` | 170 | 0 | +170 |
| `ingesta/tests/factories.py` | 90 | 0 | +90 |
| `auth/tests/factories.py` | 35 | 0 | +35 |
| `crm/tests/test_factories.py` | 95 | 0 | +95 |
| `docs/api-reference.md` | 150 | 0 | +150 |
| `docs/testing-guide.md` | 120 | 0 | +120 |
| `docs/audio-briefing.md` | 40 | 0 | +40 |
| `SECURITY.md` | 35 | 0 | +35 |
| `CONTRIBUTING.md` | 50 | 0 | +50 |
| `docs/changelog/FASE-07-cambios.md` | 85 | 0 | +85 |
| `README.md` | +15 | -5 | +10 |
| `docs/er_completo.png` | 590KB | 0 | +590KB | |
