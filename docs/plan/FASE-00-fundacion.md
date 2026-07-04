# FASE 00: Fundación — README, LICENSE, CI/CD, Estructura

---

## Metadatos

| Campo | Valor |
|-------|-------|
| **ID** | FASE-00 |
| **Nombre** | Fundación del proyecto |
| **Prioridad** | 🔴 P0 — Urgente |
| **Horas estimadas** | 4h |
| **Dependencias** | Ninguna |
| **Estado** | Pendiente |
| **Inicio planeado** | 2026-07-02 |

---

## Objetivo

Establecer la base documental y de infraestructura del proyecto para que sea mantenible, desplegable y entendible por cualquier desarrollador que se una al equipo.

---

## Reglas de Ejecución

1. **Documentación de cambios** → generar `docs/changelog/FASE-00-cambios.md`
2. **Tests** → todo archivo nuevo de código DEBE tener test (excepto markdown, configs)
3. **Type hints** → cualquier código Python nuevo debe tener type hints completos
4. **Docstrings** → funciones públicas nuevas deben tener docstrings estilo NumPy
5. **Atomicidad** → cada commit debe dejar el proyecto funcionando. Commit por tarea completada.
6. **Independencia** → esta fase no modifica ninguna lógica de negocio existente
7. **No romper nada** → verificar que `python manage.py check` y `pytest` sigan pasando

---

## Checklist de Tareas

### Tarea 00.1 — README.md profesional
- [ ] Template estándar: descripción, captura, stack, instalación, configuración, desarrollo, deploy, testing, license
- [ ] Incluir badges de CI/CD, Python version, Django version (una vez configurados)
- [ ] Incluir enlaces a documentación en `docs/`

### Tarea 00.2 — LICENSE
- [ ] Elegir licencia (MIT recomendado para proyecto comercial interno)
- [ ] Crear archivo `LICENSE` en raíz
- [ ] Agregar cabecera de licencia en `sama_core/settings.py` (comentario)

### Tarea 00.3 — CHANGELOG.md
- [ ] Crear `CHANGELOG.md` con formato Keep a Changelog
- [ ] Primera entrada: "2026-07-02 — Baseline del proyecto"
- [ ] Entradas por cada fase completada

### Tarea 00.4 — .gitignore mejorado
- [ ] Agregar `*.egg-info/`, `*.pyc`, `.pytest_cache/`, `htmlcov/`, `.coverage`
- [ ] Agregar `docs/analysis/`, `docs/plan/`, `docs/changelog/` (seguimiento interno)
- [ ] Verificar que `docs/` NO esté ignorado (actualmente `.gitignore` ignora `docs/` completo)
- [ ] Mantener exclusiones para `.env`, `db.sqlite3`, `media/`, `.venv/`

### Tarea 00.5 — GitHub Actions CI/CD
- [ ] Crear `.github/workflows/ci.yml`
- [ ] Jobs: lint (ruff o flake8), type check (mypy), test (pytest), build check
- [ ] Python 3.12, PostgreSQL service container, Chrome para Selenium
- [ ] Cache de pip para builds rápidos

### Tarea 00.6 — pyproject.toml o setup.cfg
- [ ] Crear `pyproject.toml` con metadatos del proyecto
- [ ] Configurar herramienta de linting (ruff)
- [ ] Configurar pytest con opciones de cobertura
- [ ] Especificar versión de Python (>=3.12)

### Tarea 00.7 — Mover scripts `__` a directorio scripts/
- [ ] Crear `scripts/` directorio
- [ ] Mover todos los `__*.py` de la raíz a `scripts/`
- [ ] Mover `demo_audio_briefing.py`, `test_piper_gpu.py`, `seed_instances.py`
- [ ] Mover `check_migrations.py`, `find_syntax.py`, `fix_migrations.py`, `patch_analytics.py`, `patch_step.py`
- [ ] Mover `run_dashboard_tests.py`
- [ ] Mover archivos huérfanos (`0`, `debug_lines.txt`, `debug_orig.js`, `evo_manager_bundle.js`, `manager.html`, `manager_index.html`, `temp_original.js`, logs)

### Tarea 00.8 — Verificar integridad post-cambios
- [ ] `python manage.py check` pasa sin errores
- [ ] `python manage.py makemigrations --check` sin cambios pendientes
- [ ] `pytest crm/tests/test_views.py -x` pasa
- [ ] `pytest tenants/tests/ -x` pasa
- [ ] Los tests Selenium no se ejecutan (requieren Chrome) pero se verifica que no rompen sintaxis

---

## Archivos Afectados

| Archivo | Acción | Riesgo |
|---------|--------|--------|
| `README.md` | Crear | Bajo |
| `LICENSE` | Crear | Bajo |
| `CHANGELOG.md` | Crear | Bajo |
| `.github/workflows/ci.yml` | Crear | Bajo |
| `pyproject.toml` | Crear | Medio (puede afectar cómo pip/django lee config) |
| `.gitignore` | Modificar | Bajo |
| `scripts/__*.py` (15 archivos) | Mover | Bajo (no se importan) |
| `.gitignore` | Modificar exclusión de docs/ | **Medio** — actualmente `docs/` está ignorado |

> ⚠️ **ATENCIÓN:** El `.gitignore` actual ignora `docs/` completo. Esto significa que TODOS los archivos de documentación (incluyendo SDDs, auditorías, y estos planes) no están versionados. **Hay que quitar `docs/` del `.gitignore` o específicamente incluir los archivos necesarios.**

---

## Criterios de Aceptación

1. ✅ Cualquier persona nueva en el equipo puede leer `README.md` y entender el proyecto
2. ✅ La licencia está claramente definida en `LICENSE`
3. ✅ Hay un registro de cambios (`CHANGELOG.md`)
4. ✅ El CI corre automáticamente en cada push a main/PR
5. ✅ Los scripts de diagnóstico están organizados en `scripts/`
6. ✅ La raíz del proyecto está limpia de archivos huérfanos
7. ✅ La documentación en `docs/` está versionada (no ignorada por git)
8. ✅ `pytest` y `manage.py check` pasan

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
