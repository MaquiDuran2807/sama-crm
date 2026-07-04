# Testing Guide — SAMA AdTech

## Quick Start

```bash
# All tests
pytest

# With coverage
pytest --cov=crm --cov=tenants --cov=auth --cov=ingesta --cov=core --cov-report=term-missing

# Coverage HTML report
pytest --cov=crm --cov=tenants --cov=auth --cov=ingesta --cov=core --cov-report=html
# → open htmlcov/index.html
```

## Test Structure

```
crm/tests/
├── conftest.py              # Shared fixtures (tenant, pipeline, user, contact, lead, tag, product)
├── factories.py             # Factory Boy factories for all CRM models
├── test_factories.py        # Factory validation tests
├── test_views.py            # API CRUD + endpoint tests
├── test_drag_drop.py        # Drag & drop API logic
├── test_drag_drop_real.py   # Selenium ActionChains drag & drop + filters
├── test_domain_services.py  # Service layer tests
├── test_contact_sync.py     # WhatsApp sync webhook tests
├── test_security.py         # Auth, permissions, throttle
├── test_admin.py            # Admin configuration
├── test_commands.py         # Management commands
├── test_seed_solar_client_command.py
└── test_ui_selenium.py      # Legacy Selenium smoke tests

tenants/tests/
├── conftest.py
├── factories.py
├── test_views.py
└── test_admin.py

auth/tests/
├── conftest.py
├── factories.py
├── test_models.py
├── test_services.py
├── test_views.py
└── test_web_login_redirects.py

ingesta/tests/
├── conftest.py
├── factories.py
├── test_models.py
├── test_ingestion_service.py
├── test_summary_service.py
└── test_audio_service.py

core/tests/
├── conftest.py
├── test_models.py
└── test_views.py
```

## Test Categories

### API Tests (fast, no browser)
- `test_views.py` — CRUD para Contact, Lead, stages, tasks, tags
- `test_drag_drop.py` — Stage changes, reopen, soft delete, restore
- `test_domain_services.py` — Pipeline stats, lead summary
- `test_security.py` — Permissions, throttle, XSS, CSRF

### Selenium Tests (requires browser, slow)
- `test_drag_drop_real.py` — True drag & drop with ActionChains, filter behavior
- `test_ui_selenium.py` — Legacy smoke tests (deprecated)

### Factory Validation Tests (fast)
- `test_factories.py` — Verifies all factories generate valid model instances

## Individual Test Runs

```bash
# Factories
pytest crm/tests/test_factories.py -v

# Drag & drop real (requires Selenium):
pytest crm/tests/test_drag_drop_real.py::TestDragDropRealBehavior -v
pytest crm/tests/test_drag_drop_real.py::TestFiltersFunctional -v

# Fast API tests:
pytest crm/tests/test_views.py -v
pytest crm/tests/test_drag_drop.py -v
pytest tenants/tests/test_views.py -v
```

## Factories

Available factories (see individual `factories.py` per app):

| App | Factory | Creates |
|-----|---------|---------|
| tenants | `TenantFactory` | Tenant with unique slug |
| tenants | `PipelineConfigFactory` | PipelineConfig with 6 stages |
| tenants | `CustomFieldFactory` | Custom field for contact/lead |
| tenants | `TenantModuleFactory` | Active module for tenant |
| tenants | `TenantUserFactory` | User–Tenant membership |
| crm | `ContactFactory` | Contact with Faker data |
| crm | `LeadFactory` | Lead with auto-generated pipeline |
| crm | `LeadSourceFactory` | Lead source (platform, UTM) |
| crm | `TagFactory` | Tag with unique name per tenant |
| crm | `LeadTagFactory` | Lead–Tag relation |
| crm | `LeadActivityFactory` | Activity history entry |
| crm | `LeadTaskFactory` | Task with due date |
| crm | `ProductFactory` | Product with SKU and price |
| crm | `LeadProductFactory` | Lead–Product relation |
| crm | `KpiMetricTypeFactory` | KPI metric definition |
| crm | `KpiTargetFactory` | KPI target for tenant |
| auth | `UserFactory` | Django User (password: testpass123) |
| auth | `LoginAttemptFactory` | Login attempt record |
| auth | `PasswordResetTokenFactory` | Password reset token |
| ingesta | `EvolutionInstanceFactory` | Evolution API instance |
| ingesta | `ChatUserFactory` | WhatsApp chat user |
| ingesta | `MessageFactory` | Message with external_id |
| ingesta | `UserInteractionFactory` | Call/note interaction |
| ingesta | `DailyTextSummaryFactory` | Daily AI summary |
| ingesta | `MonthlyTextSummaryFactory` | Monthly AI summary |
| ingesta | `IngestionControlFactory` | Sync control record |
| ingesta | `SummaryExecutionControlFactory` | Summary run record |

## Coverage Targets

| App | Target | Current |
|-----|--------|---------|
| crm domain | 90%+ | ~87% |
| crm views | 80%+ | See coverage report |
| tenants | 80%+ | See coverage report |
| auth | 80%+ | See coverage report |
| ingesta | 70%+ | See coverage report |

## Known Gaps (Dashboard UI)

Antes los tests de Selenium solo verificaban atributos HTML sin simular comportamiento real. Se corrigió con `test_drag_drop_real.py` que usa ActionChains para drag real, validación DOM post-drag, y tests de filtros funcionales.

## Notes

- Run with `DJANGO_SETTINGS_MODULE=sama_core.settings.development` (default in pyproject.toml)
- Selenium tests require ChromeDriver in PATH
- Factories use `skip_postgeneration_save = True` for UserFactory and LeadFactory (suppresses deprecation warnings)
