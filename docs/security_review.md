# Security Review — CRM & Tenants Apps

**Date:** 2026-05-08  
**Scope:** `tenants` and `crm` Django apps, including REST API, HTML views, admin, and serializers.

---

## Findings Summary

| ID | Severity | Status | Description |
|----|----------|--------|-------------|
| S-01 | **CRITICAL** | ✅ Fixed | No authentication on any API endpoint |
| S-02 | **HIGH** | ✅ Fixed | `tenant` field writable in `LeadDetailSerializer` |
| S-03 | **MEDIUM** | ✅ Documented | Webhook endpoint allows unauthenticated access |
| S-04 | **MEDIUM** | ✅ Verified | No permission classes on admin views (by design) |
| S-05 | **LOW** | ✅ Verified | No SQL injection vectors found |
| S-06 | **LOW** | ✅ Verified | XSS mitigated by Django template auto-escaping |
| S-07 | **INFO** | — | CSRF protection active for session-based API calls |

---

## S-01: Missing Authentication on API Endpoints (CRITICAL)

**Before:** All REST endpoints (`/api/crm/*`, `/api/tenants/*`) had no authentication configured. DRF defaults to `AllowAny` when no `DEFAULT_PERMISSION_CLASSES` is set. Any unauthenticated user could read, create, update, or delete contacts, leads, and tenant configurations.

**Fix applied:**
- Added `DEFAULT_PERMISSION_CLASSES = ['rest_framework.permissions.IsAuthenticated']` in `settings.py`.
- Added `permission_classes = [IsAuthenticated]` explicitly on `ContactViewSet`, `LeadViewSet`, and `TenantViewSet`.
- Added `SessionAuthentication` and `BasicAuthentication` as default auth classes.

**Files changed:**
- `sama_core/settings.py`
- `crm/interfaces/views.py`
- `tenants/interfaces/views.py`

---

## S-02: Tenant Field Writable in Serializer (HIGH)

**Before:** `LeadDetailSerializer` included `tenant` in its `fields` list without marking it read-only. While `perform_update` in the ViewSet overrides this, a crafted PATCH request could theoretically attempt to reassign the tenant.

**Fix applied:**
- Declared `tenant = serializers.PrimaryKeyRelatedField(read_only=True)` in `LeadDetailSerializer`.

**Files changed:**
- `crm/interfaces/serializers.py`

---

## S-03: Webhook Endpoint Without Authentication (MEDIUM)

**Finding:** The new `POST /api/crm/webhook/chat/` endpoint is intentionally open (`AllowAny`) because it is designed to be called by external services (Evolution API, WhatsApp webhooks).

**Recommendation:** In production, this endpoint should be protected by:
- An API key passed via a custom header (e.g., `X-Webhook-Secret`), or
- IP allow-listing via middleware or network rules, or
- A shared HMAC signature verified in the view.

For the MVP this is acceptable as a documented gap.

**Files:**
- `crm/interfaces/views.py` — `webhook_sync_contact` function

---

## S-04: Admin Views (MEDIUM — by design)

**Finding:** Django Admin views use Django's built-in authentication (the `AdminSite` requires `is_staff`). No additional DRF permission classes are needed for admin views.

**Verdict:** Acceptable. Admin classes expose only business-relevant fields and do not leak credentials or sensitive personal data.

**Files reviewed:**
- `crm/admin.py`
- `tenants/admin.py`

---

## S-05: SQL Injection (LOW — none found)

All database queries use Django's ORM with parameterized queries. No raw SQL, `extra()`, or unsafe string interpolation was found in either app.

---

## S-06: Cross-Site Scripting (LOW — mitigated)

Django's template engine auto-escapes all variable output by default. The inline `<script>` blocks in `lead_detail.html` use only integer and slug values (`{{ lead.id }}`, `{{ tenant.slug }}`), which are safe types.

The `csrf_token` in templates is rendered via Django's `{% csrf_token %}` tag, which is properly escaped.

---

## S-07: CSRF Protection (INFO)

DRF's `SessionAuthentication` uses Django's CSRF protection for session-based clients. API clients using `BasicAuthentication` are exempt from CSRF checks (by design). The webhook endpoint is properly exempted via `@api_view`.

---

## Recommendations for Production

1. **Add HTTPS enforcement** — `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`.
2. **Add rate limiting** — Use `django-ratelimit` or DRF's throttling classes.
3. **Audit logging** — Log all write operations (create/update/delete) with user identity and timestamp.
4. **Secrets management** — Move `SECRET_KEY` to Azure Key Vault or equivalent.
5. **Webhook auth** — Implement API key or HMAC verification for `/api/crm/webhook/chat/`.
