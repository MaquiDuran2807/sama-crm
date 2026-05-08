# SAMA Ingesta — Arquitectura, Modelos y Endpoints

## Resumen del programa
SAMA Ingesta es un microservicio Django para ingestar y procesar mensajes (principalmente WhatsApp) desde una Evolution API. Provee:
- Sincronización incremental paginada de mensajes por instancia.
- Almacenamiento de mensajes, usuarios y metadatos.
- Dashboard CRM (UI) para revisar contactos y métricas.
- Generación de resúmenes de texto (servicio IA) y "audio briefings" TTS.
- Endpoints HTTP/REST para disparar sincronizaciones, resúmenes, audio y renombrar usuarios.

Stack principal:
- Django + Django REST Framework
- Base de datos SQLite (configurable vía env)
- Integración con Evolution API para recuperación de mensajes
- Opcional: Ollama para modelos locales, Piper-TTS para audio

## Arquitectura del proyecto
- Proyecto raíz: `sama_core` (config, urls, wsgi/asgi)
- App principal: `ingesta` contiene modelos, vistas, servicios y templates.
- Directorio `management/commands` con tareas Django (backfills, ingest helpers).
- `media/` para archivos media (audio, imágenes) y `static/`, `templates/` para UI.
- Configuración por entorno mediante `.env` (variables en `sama_core/settings.py`).

Flujo principal:
1. Trigger API (`/ingesta/api/sync/`) crea job asíncrono que usa `IngestionService` para paginar la Evolution API y guardar `Message`, `ChatUser`, etc.
2. Resúmenes: `SummaryTriggerView` invoca `TextSummaryService` para generar `DailyTextSummary` y `MonthlyTextSummary` (tokens, meta, etc.).
3. Audio briefing: `AudioBriefingTriggerView` usa `AudioBriefingService` para compilar y generar TTS.
4. UI: páginas `SyncPageView`, `CrmDashboardView`, `CrmUserDetailView` sirven templates para uso humano.

## Apps y principales modelos (resumen)
Ruta: `ingesta/models.py`

### Modelos detallados (campos y tipos)

Abajo se listan los modelos definidos en `ingesta/models.py` con sus campos y tipos aproximados según el código fuente.

- EvolutionInstance
  - `instance_name` : CharField(max_length=120, unique=True)
  - `description` : CharField(max_length=255, blank=True)
  - `is_active` : BooleanField(default=True)
  - `created_at` : DateTimeField(auto_now_add=True)
  - `updated_at` : DateTimeField(auto_now=True)

- ChatUser
  - `wa_id` : CharField(max_length=64, unique=True)
  - `name` : CharField(max_length=255, blank=True)
  - `phone_number` : CharField(max_length=32, blank=True, default="", db_index=True)
  - `is_customer` : BooleanField(default=True, db_index=True)
  - `last_interaction` : DateTimeField(default=timezone.now)
  - Métodos: `display_label()` → devuelve `name (phone)` o `wa_id` como etiqueta legible.

- Message
  - `external_id` : CharField(max_length=128, unique=True)
  - `user` : ForeignKey(`ChatUser`, on_delete=models.CASCADE, related_name="messages")
  - `content` : TextField(blank=True)
  - `from_me` : BooleanField(default=False, db_index=True)
  - `direction` : CharField(max_length=16, choices=Direction.choices, default=Direction.INBOUND, db_index=True)
  - `chat_jid` : CharField(max_length=128, blank=True, default="", db_index=True)
  - `sender_wa_id` : CharField(max_length=64, blank=True, default="", db_index=True)
  - `recipient_wa_id` : CharField(max_length=64, blank=True, default="", db_index=True)
  - `quoted_external_id` : CharField(max_length=128, blank=True, default="", db_index=True)
  - `media_url` : URLField(blank=True, default="")
  - `media_file` : FileField(upload_to="ingesta/audio/", blank=True, null=True)
  - `media_mime_type` : CharField(max_length=100, blank=True, default="")
  - `message_type` : CharField(max_length=16, choices=MessageType.choices, default=MessageType.OTHER)
  - `raw_data` : JSONField(default=dict)
  - `timestamp` : DateTimeField()
  - `processed` : BooleanField(default=False)
  - Índices: `external_id`, `timestamp`, `message_type`
  - Propiedades auxiliares definidas en el modelo:
    - `is_media_message` -> True si `message_type` en {AUDIO, IMAGE, VIDEO}
    - `has_media_file`, `has_encrypted_media_file`, `has_usable_media_file`
    - `media_state` -> "NON_MEDIA" | "AVAILABLE" | "ENCRYPTED_FILE" | "NO_MEDIA"

- UserInteraction
  - `user` : ForeignKey(`ChatUser`, on_delete=models.CASCADE, related_name="interactions")
  - `interaction_type` : CharField(max_length=16, choices=InteractionType.choices, default=InteractionType.CALL)
  - `from_me` : BooleanField(default=True, db_index=True)
  - `direction` : CharField(max_length=16, choices=Direction.choices, default=Direction.OUTBOUND, db_index=True)
  - `occurred_at` : DateTimeField(db_index=True)
  - `duration_seconds` : PositiveIntegerField(null=True, blank=True)
  - `is_video` : BooleanField(default=False)
  - `source` : CharField(max_length=40, default="csv", db_index=True)
  - `source_ref` : CharField(max_length=128, blank=True, default="", db_index=True)
  - `content` : TextField(blank=True, default="")
  - `raw_data` : JSONField(default=dict)
  - `created_at` : DateTimeField(auto_now_add=True)

- IngestionControl
  - `instance` : OneToOneField(`EvolutionInstance`, on_delete=models.CASCADE, related_name="ingestion_control")
  - `last_sync_timestamp` : DateTimeField()

- SummaryExecutionControl
  - `run_key` : CharField(max_length=40, unique=True)
  - `slot_start` : DateTimeField(db_index=True)
  - `slot_end` : DateTimeField(db_index=True)
  - `status` : CharField(max_length=16, choices=Status.choices, default=Status.RUNNING, db_index=True)
  - `started_at` : DateTimeField(auto_now_add=True)
  - `finished_at` : DateTimeField(null=True, blank=True)
  - `detail` : TextField(blank=True, default="")
  - Contadores/metadatos (PositiveIntegerField): `eligible_users`, `processed_users`, `skipped_users`, `failed_users`, `processed_text_messages`, `daily_summaries_created`, `daily_summaries_updated`, `monthly_summaries_created`, `monthly_summaries_updated`, `prompt_tokens`, `completion_tokens`, `total_tokens`
  - `meta` : JSONField(default=dict)

- DailyTextSummary
  - `user` : ForeignKey(`ChatUser`, on_delete=models.CASCADE, related_name="daily_text_summaries")
  - `summary_date` : DateField(db_index=True)
  - `text` : TextField(blank=True, default="")
  - `has_data` : BooleanField(default=False)
  - `pending_items` : JSONField(default=list)
  - `mentioned_people` : JSONField(default=list)
  - `deadlines` : JSONField(default=list)
  - `payment_promises` : JSONField(default=list)
  - `source_message_count` : PositiveIntegerField(default=0)
  - `source_last_message_ts` : DateTimeField(null=True, blank=True)
  - `prompt_tokens`, `completion_tokens`, `total_tokens` : PositiveIntegerField(default=0)
  - `last_execution` : ForeignKey(`SummaryExecutionControl`, null=True, blank=True, on_delete=models.SET_NULL, related_name="daily_summaries")
  - `created_at` : DateTimeField(auto_now_add=True)
  - `updated_at` : DateTimeField(auto_now=True)

- MonthlyTextSummary
  - `user` : ForeignKey(`ChatUser`, on_delete=models.CASCADE, related_name="monthly_text_summaries")
  - `year` : PositiveSmallIntegerField(db_index=True)
  - `month` : PositiveSmallIntegerField(db_index=True)
  - `text` : TextField(blank=True, default="")
  - `has_data` : BooleanField(default=False)
  - `pending_items`, `mentioned_people`, `deadlines`, `payment_promises` : JSONField(default=list)
  - `source_message_count` : PositiveIntegerField(default=0)
  - `source_last_message_ts` : DateTimeField(null=True, blank=True)
  - `prompt_tokens`, `completion_tokens`, `total_tokens` : PositiveIntegerField(default=0)
  - `revision` : PositiveIntegerField(default=1)
  - `is_current` : BooleanField(default=True, db_index=True)
  - `last_execution` : ForeignKey(`SummaryExecutionControl`, null=True, blank=True, on_delete=models.SET_NULL, related_name="monthly_summaries")
  - `created_at` : DateTimeField(auto_now_add=True)
  - `updated_at` : DateTimeField(auto_now=True)

Si quieres, puedo añadir los fragmentos de modelo exactos (copiar las definiciones de `ingesta/models.py`) o generar una tabla CSV/Markdown con los campos y tipos por modelo.

## Estructura de vistas y lógica
Ruta principal: `ingesta/views.py`

- Views basadas en DRF `APIView` para APIs asíncronas y de estado:
  - `SyncTriggerView` (POST): inicia job de sincronización asíncrono (usa `IngestionService`).
  - `SyncStatusView` (GET): devuelve estado del job `{job_id, status, progress, message, result, error}`.
  - `InstancesListView` (GET): lista instancias activas de Evolution.
  - `ChatUserRenameView` (POST): renombra usuario (valida existencia).
  - `SummaryTriggerView` (POST): inicia job asíncrono para generar resúmenes IA (usa `TextSummaryService`).
  - `AudioBriefingTriggerView` (POST): inicia job asíncrono para generar audio briefing (usa `AudioBriefingService`).
  - `EndpointDocsView` (GET): endpoint de documentación programática (JSON) sobre endpoints expuestos.

- Views basadas en `django.views.View` para UI:
  - `SyncPageView` (GET): página con UI para disparar sync y ver progreso.
  - `CrmDashboardView` (GET): compone métricas y tablas para dashboard CRM; uso intensivo de ORM (counts, agregaciones, filtros de querystring).
  - `CrmUserDetailView` (GET/POST): muestra ficha detalle de usuario; POST permite renombrar (redirect en UI).
  - `HomeView` (GET): home con lista de endpoints en template.

Lógica asíncrona:
- Los endpoints de trigger crean un `job_id` y lanzan un `threading.Thread(..., daemon=True)` que ejecuta el servicio (IngestionService, TextSummaryService, AudioBriefingService). Estado y progreso se mantienen en el dict global `SYNC_JOBS` protegido por `SYNC_JOBS_LOCK`.
- `on_progress` y `on_summary_progress` callbacks actualizan `SYNC_JOBS` para seguimiento.

Errores y manejo:
- Los runners capturan excepciones, hacen `logger.exception(...)` y actualizan el job con `status='failed'`, `error` y `traceback`.
- Las vistas API devuelven códigos HTTP apropiados (p. ej. 202 Accepted para inicio de job, 404 cuando job_id no existe, 400 para parámetros faltantes, 200 para respuestas exitosas).

## Endpoints documentados (resumen)
Base: `/ingesta/` (incluido en `sama_core/urls.py`)

- GET `/` (Home)
  - Descripción: UI principal y lista de endpoints.
  - Respuesta: HTML renderizado.

- GET `/api/docs/`
  - Descripción: devuelve JSON con catálogo de endpoints.
  - Respuesta ejemplo: {"name": "SAMA Ingestion API", "version": "sprint-1", "endpoints": [...]}
  - Código: 200 OK

- GET `/ingesta/sync/` (SyncPageView)
  - UI para disparar sincronizaciones (HTML).

- POST `/ingesta/api/sync/` (SyncTriggerView)
  - Body: JSON {"instance_name": "default"} (opcional)
  - Acción: crea job asíncrono para sincronizar desde Evolution API
  - Respuesta: 202 Accepted
    - Ejemplo: {"job_id": "uuid", "status": "queued", "progress": 0, "message": "Tarea creada"}
  - Errores: si ocurre excepción en el runner, job será marcado `failed` y `/status/` mostrará `error` y `traceback`.

- GET `/ingesta/api/sync/<job_id>/status/` (SyncStatusView)
  - Respuesta: 200 OK con contenido del job dict o 404 si no existe
  - Ejemplo: {"job_id": "...", "instance_name": "default", "status": "queued|running|completed|failed", "progress": 0, "message": "texto", "result": {...}, "error": null}

- POST `/ingesta/api/summary/` (SummaryTriggerView)
  - Body: {"lookback_hours": 12, "force": false, "accumulate": true}
  - Acción: inicia generación de resúmenes IA en background
  - Respuesta: 202 Accepted con `{job_id, status, progress, message}`
  - Resultado final en status result: incluye `daily_generated` y `monthly_generated` con listados y metadatos.
  - Manejo de errores: similar a sync, `failed` con `error` y `traceback`.

- POST `/ingesta/api/audio-briefing/` (AudioBriefingTriggerView)
  - Body: {"instance_name": "default", "team_user_id": <id>|null}
  - Acción: genera briefing de audio (TTS) para usuario de equipo seleccionado
  - Respuesta: 202 Accepted con `{job_id, status, progress, message}`
  - Resultado final: `result` puede contener `audio_download_url`, `delivery_mode`, `selected_team_user` y `error` en caso de fallo.

- GET `/ingesta/api/instances/` (InstancesListView)
  - Respuesta: 200 OK con lista de instancias activas: [{"id": 1, "instance_name": "default", "description": "..."}]

- POST `/ingesta/api/chat-users/rename/` (ChatUserRenameView)
  - Body: {"user_id": 1, "name": "Nombre cliente"}
  - Validaciones: `user_id` requerido; retorna 400 si no enviado; 404 si no existe.
  - Respuesta: 200 OK con usuario actualizado: {"id","wa_id","phone_number","name","display_label"}

- GET `/ingesta/crm/` (CrmDashboardView)
  - UI HTML con métricas, filtros de querystring (`q`, `name_status`, `sort_by`, `limit`, `min_inbound`, etc.)

- GET `/ingesta/crm/user/<user_id>/` y POST same (CrmUserDetailView)
  - GET: renderiza ficha de usuario con mensajes y resúmenes (HTML)
  - POST: recibe `name` en form-data para renombrar (redirección)

Códigos de error y convenciones generales:
- 202 Accepted: cuando se inicia una tarea asíncrona (sync, summary, audio).
- 200 OK: respuesta con datos o confirmación (rename, status polling, instances list).
- 400 Bad Request: parámetros faltantes o inválidos (ej. `user_id` ausente en rename).
- 404 Not Found: recursos no encontrados (ej. job_id o usuario).
- En ejecuciones asíncronas, errores del runner se conservan en `SYNC_JOBS[job_id]['error']` y `traceback` para inspección.

## Notas operativas y configuraciones importantes
- Variables relevantes en `sama_core/settings.py`:
  - `EVOLUTION_BASE_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCES_ENDPOINT`, `EVOLUTION_MESSAGES_ENDPOINT` para la API fuente.
  - `OLLAMA_BASE_URL`, `OLLAMA_MODEL` para IA local.
  - `PIPER_VOICE_MODEL`, `PIPER_USE_GPU`, y parámetros de audio.
  - `MEDIA_ROOT` y `MEDIA_URL` para servir artefactos (archivos TTS, medios).
- Cursor de sincronización: `IngestionControl.last_sync_timestamp` por `EvolutionInstance`.
- Deduplicación de mensajes por `Message.external_id` (unique).

## Archivos relevantes (puntos de entrada)
- [sama_core/settings.py](sama_core/settings.py)
- [sama_core/urls.py](sama_core/urls.py)
- [ingesta/models.py](ingesta/models.py)
- [ingesta/views.py](ingesta/views.py)
- [ingesta/urls.py](ingesta/urls.py)
- `ingesta/services.py`, `ingesta/audio_service.py`, `ingesta/summary_service.py` (lógica de negocio; revisar para detalles de integración con Evolution/Ollama/Piper)

---
Si quieres, puedo:
- Expandir la sección de modelos con la lista completa de campos y tipos para cada modelo (más detallado).
- Incluir ejemplos de request/responses concretos en formato JSON para cada endpoint.
- Extraer y documentar funciones y métodos clave de `services.py`, `audio_service.py` y `summary_service.py`.

¿Qué prefieres que haga ahora?