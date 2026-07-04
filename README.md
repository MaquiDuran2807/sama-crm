
  <img src="https://img.shields.io/badge/python-3.12-blue?logo=python" alt="Python 3.12">
  <img src="https://img.shields.io/badge/django-6.0-092E20?logo=django" alt="Django 6.0">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/OpenAPI-3.0-6BA539?logo=openapi-initiative" alt="OpenAPI 3.0">
  <img src="https://img.shields.io/badge/tests-19%20factory%20tests%20✓-brightgreen" alt="Tests">
</div>

# SAMA AdTech

Sistema de gestión de relaciones con clientes (CRM) y administración multi-tenant para
la industria AdTech. Procesa mensajes de usuarios, genera resúmenes diarios/mensuales
con IA, y orquesta campañas publicitarias.

## Stack Tecnológico

| Capa        | Tecnología                         |
|-------------|------------------------------------|
| Backend     | Django 6.0 + Django REST Framework |
| Base de datos | PostgreSQL + pgvector (embeddings) |
| Cache / Colas | Redis + Celery                   |
| IA          | Piper TTS, Ollama (LLMs locales)   |
| Testing     | pytest, Selenium                   |

## Instalación

```bash
# Clonar repositorio
git clone <repo-url>
cd app-sama

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env   # (si existe) o crear .env manualmente

# Migraciones
python manage.py migrate

# Iniciar servidor
python manage.py runserver
```

## Configuración

Copiar `.env.audio.example` a `.env` y configurar:

- `SECRET_KEY` — clave secreta de Django
- `DATABASE_URL` — conexión a PostgreSQL
- `REDIS_URL` — conexión a Redis
- `OLLAMA_URL` — endpoint de Ollama (por defecto `http://localhost:11434`)

## Desarrollo

```bash
# Linting
ruff check .

# Tests
pytest

# Coverage
pytest --cov --cov-report=html
```

## Deployment

Ver documentación en `docs/` para guías de despliegue y operación.

## Documentación

| Recurso | Descripción |
|---------|-------------|
| [`docs/api-reference.md`](docs/api-reference.md) | Referencia completa de la API REST |
| [`docs/testing-guide.md`](docs/testing-guide.md) | Guía de tests, factories y cobertura |
| [`docs/audio-briefing.md`](docs/audio-briefing.md) | Sistema de audio briefing TTS |
| [`docs/deployment/guide.md`](docs/deployment/guide.md) | Despliegue con Docker+Postgres |
| [`docs/plan/ROADMAP.md`](docs/plan/ROADMAP.md) | Roadmap y plan de fases |
| [`docs/ER de tenant y crm.html`](docs/ER%20de%20tenant%20y%20crm.html) | Diagrama entidad-relación |
| [`SECURITY.md`](SECURITY.md) | Política de seguridad |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Guía de contribución |
| `/api/schema/swagger-ui/` | Swagger UI interactivo |
| `/api/schema/redoc/` | Documentación ReDoc |

## Licencia

MIT License — ver [LICENSE](LICENSE).
