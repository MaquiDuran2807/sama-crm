# FASE-06 — Preparación para producción

**Fecha:** 2026-07-03  
**Horas invertidas:** ~4h  
**Estado:** Completada

## Cambios Realizados

### Settings Multi-Entorno (Tarea 06.6)
- `sama_core/settings.py` → reemplazado por paquete `sama_core/settings/`
  - `base.py`: Configuración común (apps, middleware, REST, seguridad, Celery, etc.)
  - `development.py`: DEBUG=True, SQLite, LocMemCache, seguridad relajada
  - `production.py`: DEBUG=False, PostgreSQL, RedisCache, seguridad estricta (HSTS, SSL)
  - `__init__.py`: Importa development por defecto (compatibilidad hacia atrás)
- `manage.py`: `DJANGO_SETTINGS_MODULE` → `sama_core.settings.development`
- `wsgi.py`, `asgi.py`: mismo cambio
- `celery.py`: mismo cambio
- `pyproject.toml`: pytest apunta a `sama_core.settings.development`

### Docker (Tareas 06.1, 06.2, 06.3)
- `Dockerfile`: Base python:3.12-slim, gunicorn, collectstatic en build
- `.dockerignore`: Excluye .venv, media, logs, etc.
- `docker-compose.yml`: Stack completo para desarrollo (web, db:postgres16, redis:7, celery_worker, celery_beat)
  - Healthchecks en db y redis
  - Volúmenes persistentes
  - Variables de entorno configurables
- `docker-compose.prod.yml`: Stack para producción
  - `restart: always`, logging JSON, redes separadas (frontend/backend)
  - nginx reverse proxy incluido
  - Sin volume mounts de código

### Base de Datos y Redis (Tareas 06.4, 06.5)
- `requirements.txt`: Agregado `gunicorn`
- `.env.example`: Template completo con todas las variables documentadas
- Configuración de Celery y Redis ya existente en base.py

### Nginx (Tarea 06.8)
- `nginx/nginx.conf`: Reverse proxy con serving de static/media, proxy_pass a gunicorn

### Documentación
- `docs/deployment/guide.md`: Guía completa de despliegue (dev + prod, backup, actualización, troubleshooting)

## Checklist de Aceptación

- [x] `docker-compose up` levanta todo el stack (verificado estructuralmente)
- [x] Migraciones corren contra PostgreSQL sin errores (settings verificados)
- [x] Celery worker + beat funcionan (configurados en compose)
- [x] DEBUG=False funciona (production.py configurado)
- [x] `python manage.py check --deploy` sin errores críticos (solo warnings esperados en dev)
- [x] Guía de despliegue suficiente para montar el proyecto
- [x] `.env.example` contiene todas las variables necesarias
- [x] Proyecto corre en desarrollo (SQLite sin Docker) y producción (Postgres con Docker)

## Archivos Creados

| Archivo | Descripción |
|---------|-------------|
| `sama_core/settings/__init__.py` | Package init, importa development |
| `sama_core/settings/base.py` | Config común |
| `sama_core/settings/development.py` | Config desarrollo |
| `sama_core/settings/production.py` | Config producción |
| `Dockerfile` | Imagen Docker |
| `.dockerignore` | Exclusiones Docker |
| `docker-compose.yml` | Stack desarrollo |
| `docker-compose.prod.yml` | Stack producción |
| `nginx/nginx.conf` | Reverse proxy |
| `.env.example` | Template de variables |
| `docs/deployment/guide.md` | Guía de despliegue |

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `manage.py` | DJANGO_SETTINGS_MODULE actualizado |
| `sama_core/wsgi.py` | DJANGO_SETTINGS_MODULE actualizado |
| `sama_core/asgi.py` | DJANGO_SETTINGS_MODULE actualizado |
| `sama_core/celery.py` | DJANGO_SETTINGS_MODULE actualizado |
| `pyproject.toml` | pytest settings module actualizado |
| `requirements.txt` | Agregado gunicorn |

### Fixes post-build (verificación con Docker)
- `Dockerfile`: Agregado `RUN mkdir -p /app/logs /app/staticfiles` para que los directorios existan en el container
- `development.py`: La configuración de `DATABASES` ahora detecta automáticamente si el engine es PostgreSQL y expone `HOST`, `PORT`, `USER`, `PASSWORD` desde entorno; si es SQLite usa solo `NAME`
- Se eliminó `_verify.py` (script temporal de verificación)
- `rebuild.bat`: Script para reconstruir imagen y reiniciar stack con un solo comando

## Verificación en Contenedor Real

| Paso | Resultado |
|------|-----------|
| `docker build -t sama-adtech:latest` | OK — 713MB, 189 static files copiados |
| `docker run --rm sama-adtech:latest python ...` imports | OK — DEBUG=False, PostgreSQL, Redis |
| `python manage.py check --deploy` (producción) | Solo 2 warnings esperados (W009 secret key, W021 HSTS preload) |
| `docker compose up -d` | 5 servicios UP (web, db, redis, worker, beat) |
| Migraciones PostgreSQL | 100% OK — todas las migraciones aplicadas |
| `curl localhost:8000` | HTTP 200 |

## Archivos Creados (adicionales)

| Archivo | Descripción |
|---------|-------------|
| `rebuild.bat` | Script one-command para rebuild + restart del stack |

## Archivos Modificados (adicionales)

| Archivo | Cambio |
|---------|--------|
| `sama_core/settings/development.py` | DATABASES ahora soporta PostgreSQL dinámicamente |
| `Dockerfile` | Agregado `mkdir -p /app/logs /app/staticfiles` |

## Archivos Eliminados

| Archivo | Razón |
|---------|-------|
| `sama_core/settings.py` | Reemplazado por paquete `settings/` |
| `_verify.py` | Script temporal de verificación (eliminado) |
