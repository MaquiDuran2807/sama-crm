# FASE 01: Seguridad — Cross-Tenant, Autenticación, Rate Limiting

---

## Metadatos

| Campo | Valor |
|-------|-------|
| **ID** | FASE-01 |
| **Nombre** | Seguridad y control de acceso |
| **Prioridad** | 🔴 P0 — Urgente |
| **Horas estimadas** | 6h |
| **Dependencias** | Ninguna (puede ejecutarse en paralelo con Fase 00) |
| **Estado** | Pendiente |
| **Inicio planeado** | 2026-07-02 |

---

## Objetivo

Cerrar las 2 vulnerabilidades críticas y las 3 de alto riesgo identificadas en el análisis de seguridad, garantizando que ningún usuario autenticado pueda acceder a datos de otros tenants.

---

## Reglas de Ejecución

1. **Documentación de cambios** → generar `docs/changelog/FASE-01-cambios.md`
2. **Tests obligatorios** para cada fix de seguridad:
   - Test que demuestre que ANTES era vulnerable
   - Test que demuestre que DESPUÉS está protegido
3. **Type hints** en todo código nuevo o modificado
4. **Docstrings** en funciones de seguridad explicando QUÉ protegen y CÓMO
5. **Atomicidad**: un fix por commit. Si revierte un fix, los otros siguen funcionando.
6. **No cambiar comportamiento para usuarios legítimos**: solo agregar validaciones

---

## Checklist de Tareas

### Tarea 01.1 — Fix cross-tenant en vistas function-based (S-01)
- [ ] Identificar todas las `@api_view` functions en `crm/interfaces/views.py`:
  - `analytics_api`
  - `tags_list_create`, `tag_delete`
  - `kpi_targets_list_create`, `kpi_target_detail`
  - `products_list_create`, `product_detail`
  - `lead_products_list_create`, `lead_product_detail`
- [ ] Agregar `TenantAccessMixin`-style validation a cada una (o crear decorador `require_tenant_access`)
- [ ] Opción: refactorizar todas a un `TenantViewSet` genérico con herencia
- [ ] Tests: verificar que usuario del Tenant A recibe 403 al acceder a datos del Tenant B
- [ ] Tests: verificar que usuario legítimo sigue teniendo acceso normal

### Tarea 01.2 — Autenticación en SyncTriggerView (S-02)
- [ ] Cambiar `authentication_classes = []` a `[SessionAuthentication, BasicAuthentication]`
- [ ] Cambiar `permission_classes = [AllowAny]` a `[IsAuthenticated]`
- [ ] Verificar que el resto de `ingesta/views.py` también tenga auth (revisar todas las APIViews)
- [ ] Si algún endpoint necesita ser público (webhooks), documentar explícitamente y poner AllowAny con nota de seguridad
- [ ] Tests: sync endpoint sin auth → 403
- [ ] Tests: sync endpoint con auth → 202 (funciona)

### Tarea 01.3 — Validación de tenant en TenantViewSet (S-03)
- [ ] Heredar `TenantViewSet` de `TenantAccessMixin`
- [ ] Agregar filtro automático para que `get_queryset()` solo retorne tenants del usuario
- [ ] Verificar que superusuarios sigan viendo todos los tenants
- [ ] Tests: usuario sin acceso al tenant → 404/403

### Tarea 01.4 — HMAC/firma en webhook (S-04)
- [ ] Definir `WEBHOOK_SECRET` en settings (desde `.env`)
- [ ] Implementar verificación de HMAC-SHA256 en `webhook_sync_contact`
- [ ] Header esperado: `X-Webhook-Signature`
- [ ] Documentar en el código cómo generar la firma desde el cliente
- [ ] Tests: request sin firma → 403
- [ ] Tests: request con firma inválida → 403
- [ ] Tests: request con firma válida → 200/201

### Tarea 01.5 — Rate limiting global
- [ ] Instalar `django-ratelimit` o configurar DRF throttling
- [ ] Configurar throttle rates globales:
  - `anon`: 10 requests/minuto
  - `user`: 100 requests/minuto
- [ ] Excluir webhook de rate limiting (o configurar rate más alto)
- [ ] Tests: verificar que throttle se activa después de N requests

### Tarea 01.6 — Seguridad en settings para producción
- [ ] Agregar `SECURE_SSL_REDIRECT = True` (configurable por env)
- [ ] Agregar `SECURE_HSTS_SECONDS = 31536000` (configurable)
- [ ] Agregar `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- [ ] Agregar `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] Agregar `SESSION_COOKIE_SECURE = True` (cuando no DEBUG)
- [ ] Agregar `CSRF_COOKIE_SECURE = True` (cuando no DEBUG)
- [ ] Verificar que todo es configurable por env para desarrollo

### Tarea 01.7 — Audit logging básico
- [ ] Crear middleware simple de audit logging (o signal)
- [ ] Loggear: timestamp, user, action, resource_type, resource_id, ip, user_agent
- [ ] Escribir a archivo de log estructurado (JSON)
- [ ] No loggear datos sensibles (passwords, tokens)

---

## Archivos Afectados

| Archivo | Acción | Riesgo |
|---------|--------|--------|
| `crm/interfaces/views.py` | Modificar | **Alto** — múltiples vistas function-based |
| `crm/interfaces/permissions.py` | Modificar | Medio — decorador/helper nuevo |
| `tenants/interfaces/views.py` | Modificar | Medio |
| `ingesta/views.py` | Modificar | Medio |
| `sama_core/settings.py` | Modificar | Bajo |
| `requirements.txt` | Modificar (django-ratelimit) | Bajo |
| `crm/tests/test_security.py` | Crear | Bajo |
| `ingesta/tests/test_auth.py` | Crear | Bajo |

---

## Criterios de Aceptación

1. ✅ Ningún endpoint del CRM permite acceso cross-tenant
2. ✅ `SyncTriggerView` requiere autenticación
3. ✅ `TenantViewSet` filtra por tenant del usuario
4. ✅ Webhook requiere firma HMAC válida
5. ✅ Hay rate limiting configurado y funcional
6. ✅ Settings de producción (HSTS, SSL, cookies seguras) están listos
7. ✅ Audit logging captura operaciones importantes
8. ✅ Tests de seguridad pasan y demuestran que las vulnerabilidades están cerradas

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
