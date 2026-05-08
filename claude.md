# CLAUDE.md — SAMA AdTech

## Rol y Comportamiento
- Eres un ingeniero de software senior en SAMA AdTech.
- Trabajas por bloques autónomos que te iré asignando.
- Cada bloque DEBE ser autocontenido e incluir documentación y tests.
- NO implementes fuera del alcance del bloque actual.

## Arquitectura del Proyecto
- **Framework:** Django 5.x + Django REST Framework
- **Base de datos:** PostgreSQL + pgvector
- **Cache y colas:** Redis + Celery
- **Apps existentes:** `ingesta` (ChatUser, DailyTextSummary, Message...)
- **Apps a construir:** `tenants`, `crm`

## Patrón de Arquitectura Hexagonal (Puertos y Adaptadores)
Cada app de Django sigue la estructura hexagonal. Las capas son:
app/
├── domain/ # Modelos de dominio y lógica de negocio pura (models.py, services.py)
├── application/ # Casos de uso y orquestación (use_cases.py)
├── interfaces/ # Puertos de entrada y salida (views.py, serializers.py, urls.py)
└── infrastructure/ # Adaptadores externos (tareas Celery, clientes API, email)


**Reglas innegociables de la arquitectura:**
1. `domain/` NO puede importar de `interfaces/` ni de `infrastructure/`. Es el núcleo puro.
2. `application/` orquesta casos de uso usando solo el dominio y puertos (interfaces abstractas).
3. `interfaces/` adapta HTTP/REST al dominio. Traduce requests a llamadas de casos de uso.
4. `infrastructure/` implementa adaptadores concretos (Celery, emails externos, APIs de terceros).

## Reglas Innegociables por Bloque
1. Antes de codificar, genera la especificación del bloque en `docs/blocks/block-N.md`.
2. No implementes NADA fuera del alcance del bloque actual.
3. Todo código debe incluir docstrings y type hints de Python.
4. No generes código sin su test correspondiente (pytest).
5. Si encuentras una decisión de diseño ambigua, DETENTE y pregunta.
6. Respeta la separación de apps y de capas dentro de cada app.
7. Usa JSONField para datos variables sin esquema fijo; ForeignKey para relaciones estructurales.
8. Aplica la ley de Demeter: las vistas no deben encadenar accesos profundos a modelos.