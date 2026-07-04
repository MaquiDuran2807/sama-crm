# FASE-00: Cambios Realizados

**Fecha:** 2026-07-02

## Resumen

Establecimiento de la base documental y de infraestructura del proyecto.

## Archivos Creados

| Archivo | Descripción |
|---------|-------------|
| `README.md` | Documentación profesional del proyecto |
| `LICENSE` | Licencia MIT |
| `CHANGELOG.md` | Registro de cambios (formato Keep a Changelog) |
| `.github/workflows/ci.yml` | CI/CD: lint (ruff), type check (mypy), test (pytest) |
| `pyproject.toml` | Metadatos del proyecto, config de ruff y pytest |
| `docs/changelog/FASE-00-cambios.md` | Este archivo |

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `.gitignore` | Eliminada exclusión de `docs/` completo, agregadas exclusiones para `htmlcov/`, `.coverage`, `docs/analysis/` |
| `sama_core/settings.py` | Agregada cabecera SPDX-License-Identifier: MIT |
| `pytest.ini` | Eliminado (reemplazado por configuración en `pyproject.toml`) |

## Archivos Movidos a `scripts/`

### Scripts de diagnóstico (`__*.py`)
- `__analyze_decode_pending.py`
- `__daily_duration.py`
- `__diagnose_no_summaries.py`
- `__diagnose_ollama.py`
- `__diag_decode_failures.py`
- `__inspect_monthly.py`
- `__inspect_valentina_daily.py`
- `__rebuild_april_monthly.py`
- `__rebuild_valentina.py`
- `__rebuild_valentina_daily_then_monthly.py`
- `__show_summary_details.py`
- `__smoke_audio_button.py`
- `__validate_valentina_timeline.py`
- `__verify_summaries.py`

### Otros scripts
- `check_migrations.py`
- `demo_audio_briefing.py`
- `test_piper_gpu.py`
- `seed_instances.py`
- `find_syntax.py`
- `fix_migrations.py`
- `patch_analytics.py`
- `patch_step.py`
- `run_dashboard_tests.py`

### Archivos huérfanos (a `scripts/_orphan/`)
- `0`, `debug_lines.txt`, `debug_orig.js`, `evo_manager_bundle.js`
- `manager.html`, `manager_index.html`, `temp_original.js`
- `=-20260417-024538105.log`

## Verificaciones

- `python manage.py check` → **OK** (0 issues)
- `python manage.py makemigrations --check` → Migraciones pendientes pre-existentes (no causadas por esta fase)

## Pendientes Pre-existentes (no causados por esta fase)

1. Migraciones pendientes en apps `local_auth`, `core`, `crm`
2. Tests Selenium no ejecutables (falta módulo `selenium` y ChromeDriver)
3. Error `KeyError: ('local_auth', 'user')` en migraciones — requiere revisión de dependencias
