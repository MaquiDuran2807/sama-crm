# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Baseline del proyecto — estructura inicial Django 6.0 con apps `ingesta`, `tenants`, `crm`
- README profesional con stack, instalación y configuración
- LICENSE (MIT)
- CI/CD con GitHub Actions (lint, type check, test)
- Configuración de ruff y pytest en `pyproject.toml`
- Organización de scripts en `scripts/`
- Documentación de fases en `docs/plan/`

### Changed

- `sama_core/settings.py` → paquete `sama_core/settings/` con `base.py`, `development.py`, `production.py`
- Entry points (`manage.py`, `wsgi.py`, `asgi.py`, `celery.py`) ahora usan `sama_core.settings.development`

### Added

- `Dockerfile` + `.dockerignore` para contenedorización
- `docker-compose.yml` (desarrollo: web, db, redis, celery)
- `docker-compose.prod.yml` (producción: +nginx, redes separadas, logging JSON)
- `nginx/nginx.conf` — reverse proxy con static/media serving
- `.env.example` — template completo de variables de entorno
- `docs/deployment/guide.md` — guía de despliegue multi-entorno
- `requirements.txt`: agregado `gunicorn`
- `development.py`: DATABASES ahora soporta PostgreSQL dinámicamente (HOST/PORT/USER/PASSWORD)
- `Dockerfile`: agregado `mkdir -p /app/logs /app/staticfiles` para evitar errores en container
- `rebuild.bat`: script one-command para rebuild + restart del stack
