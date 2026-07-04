# FASE 04: Testing — Cobertura, Conftest, Domain Tests

---

## Metadatos

| Campo | Valor |
|-------|-------|
| **ID** | FASE-04 |
| **Nombre** | Infraestructura y cobertura de tests |
| **Prioridad** | 🟠 P1 — Alta |
| **Horas estimadas** | 10h |
| **Dependencias** | Fase 00 (estructura base, pyproject.toml) |
| **Estado** | Pendiente |
| **Inicio planeado** | 2026-07-04 |

---

## Objetivo

Llevar la cobertura de tests del 40-50% actual a >75%, eliminar duplicación de fixtures, y cubrir las áreas críticas sin test: `domain/services.py`, `ingesta/`, `core/`, `auth/`.

---

## Reglas de Ejecución

1. **Documentación de cambios** → `docs/changelog/FASE-04-cambios.md`
2. **Fixtures compartidas**: crear `conftest.py` y ELIMINAR fixtures duplicadas de tests individuales
3. **`assertNumQueries`** en tests de vistas para evitar regresiones de performance
4. **No `sleep()` en tests nuevos**: usar `WebDriverWait` para Selenium
5. **Cobertura mínima**: domain services >80%, application >80%
6. **Factory Boy / Model Bakery**: usar factories en vez de `objects.create()` directo
7. **Tests atómicos**: cada test debe poder ejecutarse solo (`pytest test_file.py::test_name`)

---

## Checklist de Tareas

### Tarea 04.1 — Crear `conftest.py` con fixtures compartidas
- [ ] Crear `crm/tests/conftest.py` con fixtures:
  - `tenant` (tenant activo con pipeline config)
  - `pipeline` (pipeline config completo)
  - `user` (usuario autenticado asociado al tenant)
  - `contact` (contacto del tenant)
  - `lead_in_lead`, `lead_in_calificacion`, `lead_closed` (leads en distintas etapas)
  - `client` (DRF APIClient autenticado)
  - `tag` (tag del tenant)
  - `product` (producto del tenant)
- [ ] Crear `tenants/tests/conftest.py` similar
- [ ] Crear `auth/tests/conftest.py`
- [ ] Migrar tests existentes para usar fixtures compartidas (NO borrar aún las duplicadas)
- [ ] Eliminar fixtures inline duplicadas de los archivos de test

### Tarea 04.2 — Tests directos para `crm/domain/services.py`
- [ ] Crear `crm/tests/test_domain_services.py`
- [ ] Tests para `change_lead_stage()`:
  - Cambio normal crea actividad
  - Cambio a etapa cerrada marca `is_closed=True`
  - Última etapa cierra automáticamente
  - Idempotencia: mismo stage no cambia nada
- [ ] Tests para `auto_advance_eligible_leads()`:
  - Lead estancado >48h avanza
  - Lead recién actualizado no avanza
  - Respeta `skip_allowed`
  - Respeta pipeline stages
  - Crea LeadActivity por cada avance
- [ ] Tests para `_next_available_stage()`:
  - Encuentra siguiente etapa
  - Salta etapas marcadas
  - Retorna None si está en última etapa
- [ ] Tests para `create_reopen_lead()`:
  - Crea lead con is_recompra=True
  - Original queda cerrado
  - Copia contact del original
  - No duplica si ya hay recompra activa
- [ ] Tests para `get_lead_summary()`:
  - Encuentra resumen existente
  - Retorna None si no hay resumen
  - Respeto por lead sin contacto (no crash)
- [ ] Tests para `get_leads_stats()`:
  - Conteos correctos por etapa
  - Leads de hoy vs totales
  - Leads cerrados ganados/perdidos

### Tarea 04.3 — Tests para `ingesta/`
- [ ] Crear `ingesta/tests/conftest.py`
- [ ] Crear `ingesta/tests/test_models.py`:
  - Creación de EvolutionInstance, ChatUser, Message
  - Unique constraints (external_id, wa_id)
  - Propiedades de Message (is_media_message, media_state, etc.)
- [ ] Crear `ingesta/tests/test_ingestion_service.py`:
  - Mockear Evolution API responses
  - Sincronización crea mensajes
  - Deduplicación por external_id
  - Incremental: solo nuevos mensajes
  - Overlap configurable funciona
- [ ] Crear `ingesta/tests/test_summary_service.py`:
  - Mockear Ollama responses
  - Generación de DailyTextSummary
  - Generación de MonthlyTextSummary
  - Idempotencia con force flag
  - Control de ejecución (SummaryExecutionControl)
- [ ] Crear `ingesta/tests/test_audio_service.py`:
  - Generación de audio briefing
  - Selección de team_user
  - Manejo de errores de TTS
- [ ] Tests para views de ingesta (endpoints de sync, summary, audio)

### Tarea 04.4 — Tests para `core/`
- [ ] Crear `core/tests/test_models.py`:
  - Page, Section, MenuItem, SiteConfiguration
- [ ] Crear `core/tests/test_views.py`:
  - HomePageView
  - PageDetailView (slug routing)
  - ContactMessage creation

### Tarea 04.5 — Tests para `auth/`
- [ ] Crear `auth/tests/test_models.py`:
  - User creation con user_type
  - LoginAttempt registro
  - PasswordResetToken expiración
- [ ] Crear `auth/tests/test_services.py`:
  - `authenticate_user()` login exitoso/fallido
  - `check_user_permission()` permisos por rol
- [ ] Crear `auth/tests/test_views.py`:
  - Login endpoint API
  - Logout
  - User profile retrieval

### Tarea 04.6 — Refactorizar tests Selenium
- [ ] Migrar `sleep()` → `WebDriverWait` en tests de `test_drag_drop_real.py`
- [ ] Migrar `sleep()` → `WebDriverWait` en `test_ui_selenium.py`
- [ ] Agregar fixture `chrome_options` reusable
- [ ] Verificar que tests no son frágiles con diferentes velocidades de red/CPU

### Tarea 04.7 — Unificar tests duplicados
- [ ] Identificar tests duplicados entre `test_views.py` y `test_drag_drop.py`
- [ ] Eliminar duplicados del archivo menos mantenido
- [ ] Mantener solo la versión más completa/robusta
- [ ] Documentar merge en changelog

### Tarea 04.8 — Configurar cobertura en pytest
- [ ] Agregar `pytest-cov` a requirements
- [ ] Configurar `pyproject.toml` con `--cov=crm --cov=tenants --cov=auth --cov=ingesta --cov=core`
- [ ] Agregar reporte HTML: `--cov-report=html`
- [ ] Establecer mínimo de cobertura (75%) como CI gate

---

## Archivos Afectados

| Archivo | Acción | Riesgo |
|---------|--------|--------|
| `crm/tests/conftest.py` | Crear | **Alto** — afecta todos los tests CRM |
| `tenants/tests/conftest.py` | Crear | Medio |
| `crm/tests/test_domain_services.py` | Crear | Bajo |
| `crm/tests/test_views.py` | Modificar | Medio |
| `crm/tests/test_drag_drop.py` | Modificar/Eliminar | Medio |
| `crm/tests/test_drag_drop_real.py` | Modificar | Medio |
| `crm/tests/test_ui_selenium.py` | Modificar | Medio |
| `ingesta/tests/` (todo) | Crear | Bajo |
| `core/tests/` (todo) | Crear | Bajo |
| `auth/tests/test_*.py` | Crear | Bajo |
| `pyproject.toml` | Modificar | Bajo |

---

## Criterios de Aceptación

1. ✅ `conftest.py` compartido en crm, tenants, auth — sin fixtures duplicadas
2. ✅ `crm/domain/services.py` tiene tests directos >80% cobertura
3. ✅ `ingesta/` tiene tests para modelos, servicios y views
4. ✅ `core/` tiene tests básicos
5. ✅ `auth/` tiene tests para modelos, servicios y views
6. ✅ Tests Selenium usan `WebDriverWait`, no `sleep()`
7. ✅ Tests duplicados eliminados o unificados
8. ✅ Cobertura total del proyecto >75%
9. ✅ Reporte HTML de cobertura generado

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
