# SDD — App crm

## Propósito
Gestiona los contactos y leads de cada tenant, con pipelines de ventas configurables, fuentes de origen, historial de actividades e integración con resúmenes de IA de la app `ingesta`.

## Modelos

### Contact
- **id** (PK)
- **tenant**: FK Tenant (CASCADE, related_name="contacts")
- **full_name**: CharField(255)
- **phone_number**: CharField(32, blank=True, db_index=True)
- **email**: EmailField(blank=True)
- **address**: TextField(blank=True)
- **city**: CharField(100, blank=True)
- **utm_source**, **utm_medium**, **utm_campaign**: CharField (blank)
- **referrer_contact**: FK self (SET_NULL, null=True, related_name="referred_contacts")
- **custom_fields**: JSONField(default=dict)
- **created_at**, **updated_at**: DateTimeField

### Lead
- **id** (PK)
- **tenant**: FK Tenant (CASCADE, related_name="leads")
- **contact**: FK Contact (CASCADE, related_name="leads")
- **current_stage**: CharField(100)
- **product_of_interest**: CharField(255, blank=True)
- **product_category**: CharField(100, blank=True)
- **notes**: TextField(blank=True)
- **skipped_stages**: JSONField(default=list)
- **is_closed**: BooleanField(default=False)
- **closed_result**: CharField(20, blank=True) — won/lost
- **custom_fields**: JSONField(default=dict)
- **created_at**, **updated_at**, **last_contacted_at**: DateTimeField

### LeadSource
- **id** (PK)
- **lead**: OneToOneField Lead (CASCADE, related_name="source")
- **platform**: CharField(choices=Platform) — meta/google/tiktok/web/referral
- **utm_source**, **utm_medium**, **utm_campaign**: CharField (blank)
- **referrer_contact**: FK Contact (SET_NULL, null=True)
- **landing_page_url**: URLField(blank)
- **created_at**: DateTimeField

### LeadActivity
- **id** (PK)
- **lead**: FK Lead (CASCADE, related_name="activities")
- **activity_type**: CharField(50) — stage_change, note_added, auto_advance
- **description**: TextField
- **performed_by**: CharField(100, default="system")
- **created_at**: DateTimeField

### Choices
- **Platform**: META, GOOGLE, TIKTOK, WEB, REFERRAL

## Servicios de dominio (domain/services.py)
- `change_lead_stage(lead, new_stage, performed_by="system")`: actualiza current_stage, crea LeadActivity con tipo "stage_change", actualiza last_contacted_at.
- `auto_advance_eligible_leads(tenant)`: avanza leads estancados (>48h en etapa no cerrada) si el tenant lo permite. Omite etapas saltadas. Crea LeadActivity.
- `get_lead_summary(lead)`: obtiene el último DailyTextSummary del ChatUser asociado al Contact del lead (usando la app ingesta).
- `get_leads_stats(tenant)`: devuelve dict con total_leads, leads_por_etapa, leads_nuevos_hoy.

## Endpoints REST
- `GET /api/crm/contacts/` — lista contactos (filtro tenant_slug, búsqueda).
- `POST /api/crm/contacts/`, `PATCH /api/crm/contacts/{id}/` — crear/editar contacto.
- `GET /api/crm/leads/` — lista leads (filtro tenant_slug, stage, contact_id).
- `POST /api/crm/leads/` — crear lead. Si se envían datos de fuente, crear LeadSource.
- `PATCH /api/crm/leads/{id}/` — cambiar etapa, notas, etc.
- `GET /api/crm/leads/{id}/summary/` — devuelve último resumen IA del contacto.
- `GET /api/crm/tenants/{slug}/stats/` — métricas del pipeline.

## Tareas Celery (infrastructure/tasks.py)
- `auto_advance_stage`: cada 4 horas, itera tenants activos y ejecuta `auto_advance_eligible_leads`.

## Templates
- `crm/dashboard.html`: vista Kanban con columnas por etapa, tarjetas de leads, buscador.
- `crm/lead_detail.html`: ficha con timeline, selector de etapa, notas, resumen IA y fuente.