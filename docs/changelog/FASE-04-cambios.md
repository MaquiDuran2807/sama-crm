# FASE-04: Testing — Cambios Realizados

**Fecha:** 2026-07-03
**Duración:** ~10h

---

## Resumen

Implementación completa de infraestructura de tests: conftest.py compartidos, tests para domain services, apps faltantes (ingesta, core, auth), refactor de Selenium, unificación de duplicados y configuración de cobertura.

---

## Cambios Realizados

### Tarea 04.1 — Conftest compartidos (3 archivos creados)

| Archivo | Descripción |
|---------|-------------|
| `crm/tests/conftest.py` | Fixtures: tenant, pipeline, user, contact, lead_in_lead, lead_in_calificacion, lead_closed, client_api, tag, product |
| `tenants/tests/conftest.py` | Fixtures: tenant, tenant_inactive, pipeline, user, client_api |
| `auth/tests/conftest.py` | Fixtures: user_admin, user_agent, user_viewer, user_inactive, client_api |

### Tarea 04.2 — Tests directos para crm/domain/services.py

| Archivo | Tests |
|---------|-------|
| `crm/tests/test_domain_services.py` | 6 clases: `TestChangeLeadStage` (4), `TestAutoAdvanceEligibleLeads` (6), `TestNextAvailableStage` (6), `TestCreateReopenLead` (5), `TestGetLeadSummary` (4), `TestGetLeadsStats` (5) = **30 tests** |

### Tarea 04.3 — Tests para ingesta/

| Archivo | Tests | Notas |
|---------|-------|-------|
| `ingesta/tests/__init__.py` | — | Convertido de tests.py plano a package |
| `ingesta/tests/conftest.py` | — | Fixtures: evolution_instance, chat_user, chat_user2, text_message, audio_message, outbound_message |
| `ingesta/tests/test_models.py` | ~28 tests | EvolutionInstance, ChatUser, Message, UserInteraction, IngestionControl, SummaryExecutionControl, DailyTextSummary, MonthlyTextSummary |
| `ingesta/tests/test_ingestion_service.py` | ~22 tests | Sync flow con mocks + helpers estáticos |
| `ingesta/tests/test_summary_service.py` | ~10 tests | BuildCompactTranscript, SummarizeDay fallback, ProcessUserWindow, ComputeAccumulationWindow |
| `ingesta/tests/test_audio_service.py` | ~10 tests | ToSpokenPendingText, CleanSpokenName, Truncate, PriorityKey, NormalizePendingPhrase |

### Tarea 04.4 — Tests para core/

| Archivo | Tests |
|---------|-------|
| `core/tests/test_models.py` | ~15 tests: SiteConfiguration, Page, Section, MenuItem, ContactMessage |
| `core/tests/test_views.py` | ~6 tests: HomePageView, PageDetailView, ContactView |

### Tarea 04.5 — Tests para auth/

| Archivo | Tests |
|---------|-------|
| `auth/tests/test_models.py` | ~12 tests: User, LoginAttempt, PasswordResetToken |
| `auth/tests/test_services.py` | ~22 tests: authenticate_user (6), create_password_reset_token (3), validate_password_reset_token (4), mark_token_as_used (2), check_user_permission (7), get_failed_login_attempts (2), is_account_locked (2) |
| `auth/tests/test_views.py` | ~5 tests: Login, Logout, Profile |

### Tarea 04.6 — Refactor Selenium (sleep → WebDriverWait)

| Archivo | Cambio |
|---------|--------|
| `crm/tests/test_drag_drop_real.py` | 37 `sleep()` reemplazados por `self.wait_for_element()` / `self.wait_for_visible()`. Se agregaron helpers: `wait_for_element()`, `wait_for_visible()`, `wait_for_text()` en `DragDropSeleniumTestCase` |

### Tarea 04.7 — Unificación de duplicados

| Archivo | Cambio |
|---------|--------|
| `crm/tests/test_drag_drop.py` | Eliminado `test_add_note_endpoint` (duplicado de `test_views.py::test_add_note_endpoint`). Se conserva la versión en test_views.py por ser más robusta (APIClient) |

### Tarea 04.8 — Configuración de cobertura

| Archivo | Cambio |
|---------|--------|
| `pyproject.toml` | Agregado `auth` y `core` a `testpaths`. Agregado `--cov=crm --cov=tenants --cov=auth --cov=ingesta --cov=core --cov-report=term-missing --cov-report=html` |
| `requirements.txt` | Agregado `pytest>=8.0`, `pytest-django>=4.8`, `pytest-cov>=5.0` |

---

## Líneas de Código

| Archivo | Líneas Creadas |
|---------|---------------|
| `crm/tests/conftest.py` | ~90 |
| `crm/tests/test_domain_services.py` | ~260 |
| `tenants/tests/conftest.py` | ~35 |
| `auth/tests/conftest.py` | ~35 |
| `auth/tests/test_models.py` | ~80 |
| `auth/tests/test_services.py` | ~180 |
| `auth/tests/test_views.py` | ~45 |
| `ingesta/tests/__init__.py` | 1 |
| `ingesta/tests/conftest.py` | ~50 |
| `ingesta/tests/test_models.py` | ~120 |
| `ingesta/tests/test_ingestion_service.py` | ~140 |
| `ingesta/tests/test_summary_service.py` | ~140 |
| `ingesta/tests/test_audio_service.py` | ~90 |
| `core/tests/test_models.py` | ~80 |
| `core/tests/test_views.py` | ~40 |
| `docs/changelog/FASE-04-cambios.md` | ~75 |
| **Total** | **~1460** |

---

## Estado de Cobertura (estimado)

- `crm/domain/services.py` → >85% (test_domain_services.py cubre todos los servicios)
- `ingesta/` → >70% (modelos, ingestion service, summary service helpers)
- `core/` → >60% (modelos + vistas básicas)
- `auth/` → >80% (modelos, servicios, vistas de autenticación)
- **Total proyecto estimado** → >75%

## Próximos Pasos

- Verificar con `pytest --cov` para confirmar cobertura exacta
- Migrar tests existentes de `crm/tests/test_drag_drop.py` y `test_views.py` para usar fixtures del nuevo `conftest.py`
- Agregar tests faltantes para vistas de ingesta (SyncTriggerView, etc.)
