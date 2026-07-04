# API Reference — SAMA AdTech

Interactive documentation available at:
- Swagger UI: `/api/schema/swagger-ui/`
- ReDoc: `/api/schema/redoc/`
- OpenAPI Schema: `/api/schema/`

Base URL: `/api/`

---

## Authentication

All endpoints require authentication unless noted. Supported methods:
- SessionAuthentication (browser)
- BasicAuthentication (API clients)

Public endpoints:
- `POST /api/crm/webhook/chat/` — HMAC-SHA256 signed webhook

---

## CRM — Contacts

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/crm/contacts/?tenant_slug=<slug>` | List contacts |
| POST | `/api/crm/contacts/` | Create contact |
| GET | `/api/crm/contacts/{id}/` | Contact detail |
| PATCH | `/api/crm/contacts/{id}/` | Partial update |
| DELETE | `/api/crm/contacts/{id}/` | Delete contact |

**Query params:** `tenant_slug` (required)

---

## CRM — Leads

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/crm/leads/` | List leads |
| POST | `/api/crm/leads/` | Create lead |
| GET | `/api/crm/leads/{id}/` | Lead detail |
| PATCH | `/api/crm/leads/{id}/` | Update lead |
| DELETE | `/api/crm/leads/{id}/` | Soft delete lead |

**Query params:** `tenant_slug` (required), `stage`, `contact_id`, `tag`, `has_tasks`

### Lead Actions

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/crm/leads/{id}/summary/` | AI summary |
| GET | `/api/crm/leads/stats/?tenant_slug=<slug>` | Pipeline stats |
| POST | `/api/crm/leads/{id}/add_note/` | Add note |
| POST | `/api/crm/leads/{id}/add_activity/` | Add activity |
| POST | `/api/crm/leads/{id}/restore/` | Restore deleted |
| GET | `/api/crm/leads/trash/` | Deleted leads |
| POST | `/api/crm/leads/{id}/reopen/` | Reopen (recompra) |
| GET/POST | `/api/crm/leads/{id}/tasks/` | List/create tasks |
| PATCH/DELETE | `/api/crm/leads/{id}/tasks/{task_id}/` | Update/delete task |
| POST | `/api/crm/leads/{id}/add_tag/` | Add tag |
| POST | `/api/crm/leads/{id}/remove_tag/` | Remove tag |

### Lead Products

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/api/crm/leads/{lead_id}/products/` | List/add products |
| PATCH/DELETE | `/api/crm/leads/{lead_id}/products/{product_id}/` | Update/remove |

---

## CRM — Tags

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/api/crm/tenants/{slug}/tags/` | List/create tags |
| DELETE | `/api/crm/tenants/{slug}/tags/{id}/` | Delete custom tag |

---

## CRM — Products

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/api/crm/tenants/{slug}/products/` | List/create products |
| GET/PATCH/DELETE | `/api/crm/tenants/{slug}/products/{id}/` | Product detail |

---

## CRM — KPI Targets

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/api/crm/tenants/{slug}/kpi-targets/` | List/create KPI targets |
| GET/PATCH/DELETE | `/api/crm/tenants/{slug}/kpi-targets/{id}/` | KPI target detail |

---

## CRM — Analytics

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/crm/analytics/{tenant_slug}/` | Full pipeline analytics |

**Query params:** `days` (default 30), `source` (platform filter)

---

## CRM — Webhook

| Method | URL | Auth |
|--------|-----|------|
| POST | `/api/crm/webhook/chat/` | HMAC-SHA256 |

Syncs a WhatsApp contact to CRM. Body: `{phone_number, tenant_slug, full_name?}`.
Signature in `X-Webhook-Signature` header.

---

## Tenants

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/tenants/` | List accessible tenants |
| GET | `/api/tenants/{slug}/` | Tenant detail |
| GET | `/api/tenants/{slug}/pipeline/` | Pipeline stages |
| GET | `/api/tenants/{slug}/modules/` | Active modules |
| GET | `/api/tenants/{slug}/custom-fields/` | Custom fields |
| GET/PATCH | `/api/tenants/{slug}/pipeline-config/` | Pipeline config |

---

## Auth

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/login/` | Login |
| POST | `/api/auth/logout/` | Logout |
| POST | `/api/auth/password-reset/` | Request reset |
| POST | `/api/auth/password-reset/confirm/` | Confirm reset |
| GET | `/api/auth/permissions/` | User permissions |

---

## Ingesta (WhatsApp Sync)

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/ingesta/api/sync/` | Trigger message sync |
| GET | `/ingesta/api/sync-status/` | Sync status |
| POST | `/ingesta/api/trigger-summary/` | Trigger AI summary |
| POST | `/ingesta/api/trigger-audio-briefing/` | Trigger audio briefing |
| PATCH | `/ingesta/api/rename-user/{id}/` | Rename chat user |
| GET | `/ingesta/api/instances/` | List Evolution instances |

---

## Error Format

All errors return:
```json
{"detail": "Mensaje de error"}
```

Or for validation errors:
```json
{"field_name": ["Error description"]}
```

**Status codes:**
- `200` OK
- `201` Created
- `204` Deleted
- `400` Bad request
- `403` Forbidden
- `404` Not found
- `429` Rate limited

---

## Flow Diagrams

### Lead Lifecycle
```
Contact → Lead (stage: "Lead") → Calificacion → Propuesta → Negociacion → Cerrado (Ganado/Perdido)
                                                                              ↓
                                                                        Reopen (recompra)
                                                                              ↓
                                                                         Nuevo Lead
```

### WhatsApp Sync Flow
```
Evolution API → Webhook (POST /api/crm/webhook/chat/) → SAMA Backend
   │                    │                                         │
   │              HMAC-SHA256                              Create/Update
   │              Verification                              ChatUser + Contact
   │                    │                                         │
   └────────────────────┘                                         └──→ CRM Lead (optional)
```

### AI Summary Flow
```
Schedule (every 5min) → SummaryExecution → Ollama API → DailyTextSummary + MonthlyTextSummary
                                              │
                                              └──→ AudioBriefing → Piper-TTS → Evolution API
```
