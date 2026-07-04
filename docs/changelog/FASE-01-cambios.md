# FASE-01: Cambios de Seguridad

## Resumen
Implementación de seguridad cross-tenant, autenticación obligatoria en APIs de ingesta, rate limiting, HMAC en webhooks y audit logging.

## Tarea 01.1 — Cross-tenant en vistas function-based (S-01)
- Creado decorador `require_tenant_access` en `crm/interfaces/permissions.py`
- Aplicado a: `analytics_api`, `tags_list_create`, `tag_delete`, `kpi_targets_list_create`, `kpi_target_detail`, `products_list_create`, `product_detail`, `lead_products_list_create`, `lead_product_detail`
- Archivos: `crm/interfaces/permissions.py`, `crm/interfaces/views.py`

## Tarea 01.2 — Autenticación en SyncTriggerView (S-02)
- Cambiadas todas las APIViews de `ingesta/views.py` de `AllowAny` a `IsAuthenticated`
- Afecta: `SyncTriggerView`, `SyncStatusView`, `InstancesListView`, `ChatUserRenameView`, `SummaryTriggerView`, `AudioBriefingTriggerView`
- `EndpointDocsView` se mantiene público (solo documentación)
- Archivo: `ingesta/views.py`

## Tarea 01.3 — Validación de tenant en TenantViewSet (S-03)
- Agregado filtro `get_queryset()` que limita a tenants donde el usuario tiene membresía
- Superusuarios siguen viendo todos los tenants
- Archivo: `tenants/interfaces/views.py`

## Tarea 01.4 — HMAC/firma en webhook (S-04)
- Agregado `WEBHOOK_SECRET` a settings (desde `.env`)
- Implementada verificación HMAC-SHA256 en `webhook_sync_contact`
- Header esperado: `X-Webhook-Signature`
- Archivos: `sama_core/settings.py`, `crm/interfaces/views.py`

## Tarea 01.5 — Rate limiting global
- Configurado DRF throttling: 10 req/min para anónimos, 100 req/min para autenticados
- Sin dependencias externas (usa throttling nativo de DRF)
- Archivo: `sama_core/settings.py`

## Tarea 01.6 — Seguridad en settings para producción
- Agregados: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- Todos configurables por env
- Archivo: `sama_core/settings.py`

## Tarea 01.7 — Audit logging básico
- Creado `AuditLogMiddleware` en `sama_core/audit_middleware.py`
- Loggea: timestamp, method, path, status, user, ip, user_agent, duration
- Log rotativo de 10MB en `logs/audit.log`
- Archivos: `sama_core/audit_middleware.py`, `sama_core/settings.py`

## Tests
- `crm/tests/test_security.py`: cross-tenant, TenantViewSet, webhook HMAC
- `ingesta/tests/test_auth.py`: [no creado — tests de auth incluidos en test_security.py]
