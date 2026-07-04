# FASE-07 Cambios — Polish, OpenAPI, Factories, Documentación

## Resumen

Fase de polish final para llevar el proyecto de funcional a profesional: documentación interactiva de API, factories para tests robustos, y consolidación de documentación.

## Cambios Realizados

### 07.1 — OpenAPI / Swagger
- **Nuevo:** `drf-spectacular` agregado a requirements.txt
- **Nuevo:** Configuración en `sama_core/settings/base.py` — `SPECTACULAR_SETTINGS`, `DEFAULT_SCHEMA_CLASS`
- **Nuevo:** URLs en `sama_core/urls.py` — `/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/`
- **Nuevo:** Decoradores `@extend_schema` y `@extend_schema_view` en ContactViewSet, LeadViewSet, TenantViewSet y todas las `@api_view` functions
- **Archivos:** `sama_core/settings/base.py`, `sama_core/urls.py`, `crm/interfaces/views.py`, `tenants/interfaces/views.py`

### 07.2 — Factory Boy
- **Nuevo:** `factory-boy` en requirements.txt
- **Nuevo:** `tenants/tests/factories.py` — TenantFactory, PipelineConfigFactory, TenantModuleFactory, CustomFieldFactory, TenantUserFactory
- **Nuevo:** `crm/tests/factories.py` — ContactFactory, LeadFactory, LeadSourceFactory, TagFactory, LeadTagFactory, LeadActivityFactory, LeadTaskFactory, ProductFactory, LeadProductFactory, KpiMetricTypeFactory, KpiTargetFactory
- **Nuevo:** `ingesta/tests/factories.py` — EvolutionInstanceFactory, ChatUserFactory, MessageFactory, UserInteractionFactory, IngestionControlFactory, SummaryExecutionControlFactory, DailyTextSummaryFactory, MonthlyTextSummaryFactory
- **Nuevo:** `auth/tests/factories.py` — UserFactory, LoginAttemptFactory, PasswordResetTokenFactory
- **Nuevo:** `crm/tests/test_factories.py` — 19 tests de validación de factories

### 07.3 — Diagrama ER
- **Pendiente:** Requiere Graphviz instalado en el sistema. Ejecutar: `python manage.py graph_models ingesta tenants crm auth core -o docs/er_completo.png`

### 07.4 — Consolidación API Docs
- **Nuevo:** `docs/api-reference.md` — referencia completa de todos los endpoints organizados por app

### 07.5 — Consolidación Test Docs
- **Nuevo:** `docs/testing-guide.md` — unifica README_TESTS.md, TESTING_FOLLOW_UP.md, TESTING_QUICK_SUMMARY.md, DASHBOARD_TEST_AUDIT.md, TEST_EXECUTION_PLAN.md, COVERAGE_MATRIX.md

### 07.6 — Consolidación Audio Docs
- **Nuevo:** `docs/audio-briefing.md` — unifica AUDIO_BRIEFING_README.md + AUDIO_BRIEFING_SUMMARY.md

### 07.7 — SECURITY.md
- **Nuevo:** `SECURITY.md` en raíz con política de seguridad, reporting y deployment checklist

### 07.8 — CONTRIBUTING.md
- **Nuevo:** `CONTRIBUTING.md` en raíz con estándares de código, testing, y PR workflow

### 07.9 — README
- **Modificado:** `README.md` — nuevos badges (OpenAPI, tests), tabla de documentación con enlaces a Swagger/ReDoc/docs

## Archivos Creados

| Archivo | Líneas |
|---------|--------|
| `tenants/tests/factories.py` | ~50 |
| `crm/tests/factories.py` | ~170 |
| `ingesta/tests/factories.py` | ~90 |
| `auth/tests/factories.py` | ~35 |
| `crm/tests/test_factories.py` | ~95 |
| `docs/api-reference.md` | ~150 |
| `docs/testing-guide.md` | ~120 |
| `docs/audio-briefing.md` | ~40 |
| `SECURITY.md` | ~30 |
| `CONTRIBUTING.md` | ~50 |
| `docs/changelog/FASE-07-cambios.md` | Este archivo |

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `requirements.txt` | +drf-spectacular, +factory-boy |
| `sama_core/settings/base.py` | +drf_spectacular, +django_extensions en INSTALLED_APPS; +SPECTACULAR_SETTINGS; +DEFAULT_SCHEMA_CLASS |
| `sama_core/urls.py` | +schema, swagger-ui, redoc URLs |
| `crm/interfaces/views.py` | +@extend_schema en todos los ViewSets y api_views |
| `tenants/interfaces/views.py` | +@extend_schema en TenantViewSet y actions |
| `README.md` | +badges, +tabla de documentación |
