# FASE 06: Producción — Docker, Deploy, PostgreSQL, Redis

---

## Metadatos

| Campo | Valor |
|-------|-------|
| **ID** | FASE-06 |
| **Nombre** | Preparación para producción |
| **Prioridad** | 🟡 P2 — Media |
| **Horas estimadas** | 8h |
| **Dependencias** | Fase 00 (estructura), Fase 02 (Celery), Fase 01 (seguridad) |
| **Estado** | Pendiente |
| **Inicio planeado** | 2026-07-05 |

---

## Objetivo

Hacer el proyecto desplegable en cualquier entorno de producción: Dockerizar la aplicación, configurar PostgreSQL, Redis, y crear guías de despliegue para distintos entornos.

---

## Reglas de Ejecución

1. **Documentación de cambios** → `docs/changelog/FASE-06-cambios.md`
2. **Tests**: verificar que settings funcionan con configuración de producción (DB Postgres, Redis, DEBUG=False)
3. **Seguridad**: NO commitear secrets en Dockerfile o docker-compose
4. **Multi-entorno**: desarrollo, staging y producción deben ser configurables por env
5. **Atomicidad**: Dockerfile y docker-compose pueden tener múltiples commits pero la aplicación debe funcionar en cada paso

---

## Checklist de Tareas

### Tarea 06.1 — Dockerfile
- [ ] Base: `python:3.12-slim`
- [ ] Instalar dependencias del sistema (gcc, libpq-dev, etc.)
- [ ] Copiar `requirements.txt` e instalar dependencias Python
- [ ] Copiar proyecto
- [ ] `EXPOSE 8000`
- [ ] `CMD ["gunicorn", "sama_core.wsgi:application", "--bind", "0.0.0.0:8000"]`
- [ ] `.dockerignore` para excluir `.venv/`, `db.sqlite3`, `media/`, `__pycache__/`, `.git/`

### Tarea 06.2 — docker-compose.yml (desarrollo)
- [ ] Servicios:
  - `web`: Dockerfile + volume mounts + ports 8000:8000
  - `db`: PostgreSQL 16 + volume persistente
  - `redis`: Redis 7 + volume persistente
  - `celery_worker`: mismo Dockerfile, comando `celery -A sama_core worker`
  - `celery_beat`: mismo Dockerfile, comando `celery -A sama_core beat`
- [ ] Variables de entorno para configuración
- [ ] Dependencias entre servicios (`depends_on`)
- [ ] Healthchecks para db y redis

### Tarea 06.3 — docker-compose.yml (producción)
- [ ] Similar a desarrollo pero con:
  - `restart: always`
  - Políticas de reinicio
  - Logging configurado (JSON driver)
  - Redes separadas (frontend/backend)
  - Sin volume mounts de código (código empaquetado en imagen)

### Tarea 06.4 — Migrar a PostgreSQL definitivamente
- [ ] Actualizar `.env.example` con configuración Postgres
- [ ] Verificar migraciones con Postgres (diferencia con SQLite: tipos de datos, índices)
- [ ] Agregar `psycopg2` a requirements (ya está)
- [ ] Verificar que `JSONField` funciona (Django 5.x+ lo soporta en ambos)
- [ ] Documentar migración: dump SQLite → import Postgres

### Tarea 06.5 — Configuración de Redis
- [ ] Agregar configuración de cache en `settings.py`:
  ```python
  CACHES = {
      'default': {
          'BACKEND': 'django.core.cache.backends.redis.RedisCache',
          'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
      }
  }
  ```
- [ ] Configurar Celery con Redis como broker
- [ ] Verificar que el sistema funciona sin Redis (degradación elegante)
- [ ] Tests opcionales con mock de Redis

### Tarea 06.6 — Settings multi-entorno
- [ ] Crear `sama_core/settings/base.py` — común
- [ ] Crear `sama_core/settings/development.py` — DEBUG=True, SQLite, etc.
- [ ] Crear `sama_core/settings/production.py` — DEBUG=False, PostgreSQL, Redis, etc.
- [ ] Actualivar `manage.py` para usar `DJANGO_SETTINGS_MODULE`
- [ ] Actualizar `pytest.ini` para apuntar a settings de test (o development)
- [ ] Verificar que `python manage.py check --deploy` no da errores

### Tarea 06.7 — Guía de despliegue
- [ ] Crear `docs/deployment/guide.md` con:
  - Requisitos (Docker, docker-compose)
  - Variables de entorno necesarias
  - Pasos: `docker-compose build`, `docker-compose up -d`
  - Migraciones: `docker-compose exec web python manage.py migrate`
  - Static files: `docker-compose exec web python manage.py collectstatic`
  - Superusuario: `docker-compose exec web python manage.py createsuperuser`
  - Monitoreo: logs con `docker-compose logs -f`
  - Backup: dump de PostgreSQL
  - Actualización: rebuild + migrate

### Tarea 06.8 — Nginx reverse proxy (opcional para producción)
- [ ] Crear `nginx/nginx.conf`
- [ ] Servir staticfiles y media
- [ ] Proxy_pass a gunicorn
- [ ] SSL con certbot (documentar)

---

## Archivos Afectados

| Archivo | Acción | Riesgo |
|---------|--------|--------|
| `Dockerfile` | Crear | Bajo |
| `Dockerfile.dev` (opcional) | Crear | Bajo |
| `docker-compose.yml` | Crear | **Alto** — puede afectar desarrollo local |
| `nginx/nginx.conf` | Crear | Bajo |
| `.dockerignore` | Crear | Bajo |
| `.env.example` | Modificar | Bajo |
| `sama_core/settings/` (directorio) | Crear | **Alto** — rompe imports existentes |
| `sama_core/settings.py` | Mover/Renombrar | **Alto** — Django lo necesita |
| `manage.py` | Modificar | Bajo |
| `pytest.ini` | Modificar | Bajo |
| `docs/deployment/guide.md` | Crear | Bajo |

> ⚠️ **ATENCIÓN:** La separación de settings en base/dev/prod es un cambio delicado. Asegurarse de que `DJANGO_SETTINGS_MODULE` esté correcto en `pytest.ini`, `manage.py`, `wsgi.py`, `asgi.py`, y Celery.

---

## Criterios de Aceptación

1. ✅ `docker-compose up` levanta todo el stack
2. ✅ Migraciones corren contra PostgreSQL sin errores
3. ✅ Celery worker + beat funcionan
4. ✅ DEBUG=False funciona (sin serving de staticfiles desde Django)
5. ✅ `python manage.py check --deploy` no tiene errores críticos
6. ✅ La guía de despliegue es suficiente para que alguien sin contexto monte el proyecto
7. ✅ `.env.example` contiene todas las variables necesarias con valores por defecto sensatos
8. ✅ El proyecto puede correr en desarrollo con SQLite (sin Docker) y en producción con Postgres (con Docker)

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
