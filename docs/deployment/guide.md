# Guía de Despliegue — SAMA AdTech

## Requisitos

- Docker 24+
- Docker Compose 2.20+
- Git

## Estructura de entornos

| Entorno      | Comando                         | DB         | Cache     | DEBUG |
|--------------|---------------------------------|------------|-----------|-------|
| Desarrollo   | `docker compose up`             | PostgreSQL | Redis     | True  |
| Producción   | `docker compose -f docker-compose.prod.yml up -d` | PostgreSQL | Redis | False |

## Variables de Entorno

Copiar `.env.example` a `.env` y ajustar:

```bash
cp .env.example .env
```

### Variables requeridas en producción

| Variable        | Descripción                    |
|-----------------|--------------------------------|
| `SECRET_KEY`    | Clave secreta de Django (>50 chars, aleatoria) |
| `DB_PASSWORD`   | Password de PostgreSQL         |
| `ALLOWED_HOSTS` | Dominios permitidos (coma separado) |
| `EVOLUTION_API_KEY` | API Key de Evolution API   |

## Despliegue en Desarrollo

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd app-sama

# 2. Configurar variables
cp .env.example .env
# Editar .env con valores adecuados

# 3. Levantar el stack
docker compose up -d

# 4. Ejecutar migraciones (primer inicio)
docker compose exec web python manage.py migrate

# 5. Crear superusuario
docker compose exec web python manage.py createsuperuser

# 6. Ver logs
docker compose logs -f
```

La aplicación estará disponible en `http://localhost:8000`.

## Despliegue en Producción

```bash
# 1. Configurar variables de entorno
export SECRET_KEY="<generar clave aleatoria de 50+ chars>"
export DB_PASSWORD="<password seguro>"
export ALLOWED_HOSTS="midominio.com,www.midominio.com"
export CORS_ALLOWED_ORIGINS="https://midominio.com"

# 2. Build y deploy
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 3. Migraciones
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# 4. Superusuario
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# 5. Verificar
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

La aplicación estará disponible en `http://midominio.com` (puerto 80).

## Comandos Útiles

### Migraciones y Base de Datos

```bash
# Migrar
docker compose exec web python manage.py migrate

# Nuevas migraciones
docker compose exec web python manage.py makemigrations

# Backup PostgreSQL
docker compose exec db pg_dump -U sama sama_prod > backup_$(date +%Y%m%d).sql

# Restore
cat backup.sql | docker compose exec -T db psql -U sama sama_prod
```

### Logs

```bash
# Todos los servicios
docker compose logs -f

# Servicio específico
docker compose logs -f web
docker compose logs -f celery_worker

# Últimas N líneas
docker compose logs --tail=100 web
```

### Actualización

```bash
# Pull de cambios (si aplica)
git pull

# Rebuild y deploy
docker compose up -d --build

# Migraciones nuevas
docker compose exec web python manage.py migrate
```

### Limpieza

```bash
# Detener sin eliminar volúmenes
docker compose down

# Detener y eliminar volúmenes (BORRA DATOS)
docker compose down -v
```

## Estructura de Archivos

```
├── Dockerfile                          # Imagen de producción
├── docker-compose.yml                  # Stack de desarrollo
├── docker-compose.prod.yml             # Stack de producción
├── .dockerignore                       # Exclusiónes Docker
├── .env.example                        # Template de variables
├── nginx/
│   └── nginx.conf                      # Reverse proxy (producción)
├── sama_core/
│   └── settings/
│       ├── __init__.py                 # Default → development
│       ├── base.py                     # Config común
│       ├── development.py              # Desarrollo (SQLite/LocMemCache)
│       └── production.py               # Producción (PostgreSQL/Redis)
└── docs/deployment/
    └── guide.md                        # Esta guía
```

## Solución de Problemas

### Error de conexión a PostgreSQL

Verificar que PostgreSQL está saludable:

```bash
docker compose ps
docker compose logs db
```

### Error de permisos en staticfiles

```bash
docker compose exec web python manage.py collectstatic --noinput
```

### Celery no procesa tareas

Verificar Redis y worker:

```bash
docker compose logs redis
docker compose logs celery_worker
docker compose exec redis redis-cli ping  # Debería responder PONG
```
