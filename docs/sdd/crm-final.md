# SDD — App crm (Versión Final Sprint 1 · 2026-05-09)

## Propósito
Gestiona los contactos y leads de cada tenant, con pipelines de ventas configurables, fuentes de origen, historial de actividades, soft delete con papelera temporal, dashboard de métricas con gráficos, reportes diarios de seguimiento e integración con resúmenes de IA de la app `ingesta`.

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
- **is_deleted**: BooleanField(default=False, db_index=True)
- **deleted_at**: DateTimeField(null=True, blank=True)
- **deleted_by**: CharField(100, blank=True)
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
- **activity_type**: CharField(50) — stage_change, note_added, auto_advance, deleted, restored, recompra, manual
- **description**: TextField
- **performed_by**: CharField(100, default="system")
- **created_at**: DateTimeField

### DailyFollowupReport (nuevo)
- **id** (PK)
- **tenant**: FK Tenant (CASCADE, related_name="followup_reports")
- **generated_at**: DateTimeField(auto_now_add=True)
- **period**: CharField(choices=Period) — morning/evening
- **leads_data**: JSONField(default=list) — lista de {lead_id, contact_name, product, stage, last_contacted_at}
- **is_read**: BooleanField(default=False)

### Choices
- **Platform**: META, GOOGLE, TIKTOK, WEB, REFERRAL
- **Period**: MORNING, EVENING

## Pipeline Configurable por Cliente
Cada tenant define su pipeline de ventas en `tenants.PipelineConfig`. Se almacena como JSONField con esta estructura:

```json
{
  "stages": [
    {"name": "Lead", "color": "#003366", "order": 1, "skip_allowed": false},
    {"name": "Calificación", "color": "#FF9933", "order": 2, "skip_allowed": true},
    {"name": "Cotización Enviada", "color": "#FF6600", "order": 3},
    {"name": "Cerrado Ganado", "color": "#00CC66", "order": 4, "is_won_stage": true},
    {"name": "Cerrado Perdido", "color": "#FF3333", "order": 5, "is_lost_stage": true}
  ],
  "allow_skip_stages": true
}
El cliente puede renombrar, reordenar, cambiar colores y añadir/quitar etapas desde su configuración. Las etapas marcadas como is_won_stage o is_lost_stage activan el modal de "error vs recompra" en el drag & drop.

Servicios de dominio (domain/services.py)
change_lead_stage(lead, new_stage, performed_by="system"): actualiza current_stage, crea LeadActivity, actualiza last_contacted_at.

auto_advance_eligible_leads(tenant): avanza leads estancados (>48h en etapa no cerrada) si el tenant lo permite, omitiendo etapas con skip_allowed=True.

get_lead_summary(lead): obtiene el último DailyTextSummary del ChatUser asociado al Contact (app ingesta).

get_leads_stats(tenant): devuelve dict con total_leads, leads_por_etapa, leads_nuevos_hoy, active_leads, won_leads.

sync_contact_from_whatsapp(tenant, phone_number, name): crea o actualiza un Contact a partir de un mensaje de WhatsApp (app ingesta).

Endpoints REST
Método	Ruta	Descripción
GET	/api/crm/contacts/	Lista contactos (filtro tenant_slug)
POST	/api/crm/contacts/	Crea contacto
PATCH	/api/crm/contacts/{id}/	Edita contacto
GET	/api/crm/leads/	Lista leads (filtro tenant_slug, stage, contact_id)
POST	/api/crm/leads/	Crea lead + LeadSource si hay datos UTM
PATCH	/api/crm/leads/{id}/	Cambia etapa, notas
DELETE	/api/crm/leads/{id}/	Soft delete (papelera 30 días, registra actividad)
POST	/api/crm/leads/{id}/restore/	Restaura lead eliminado
POST	/api/crm/leads/{id}/add_note/	Añade nota (LeadActivity tipo note_added)
POST	/api/crm/leads/{id}/add_activity/	Actividad manual (LeadActivity tipo manual)
POST	/api/crm/leads/{id}/reopen/	Nueva oportunidad desde lead cerrado (recompra)
GET	/api/crm/leads/{id}/summary/	Resumen IA del contacto
GET	/api/crm/leads/stats/	Métricas del pipeline (?tenant_slug=)
GET	/api/crm/leads/trash/	Leads en papelera (?tenant_slug=)
GET	/api/crm/tenants/{slug}/analytics/	Datos para gráficos (?days=, ?source=)
GET	/api/crm/tenants/{slug}/followup-report/	Último reporte de seguimiento no leído
PATCH	/api/crm/tenants/{slug}/followup-report/{id}/	Marcar reporte como leído
Vistas HTML y Templates
Vista	URL	Template	Descripción
DashboardView	/crm/<slug>/dashboard/	crm/dashboard.html	Kanban con drag & drop, resumen diario de seguimiento, stats, buscador
LeadDetailView	/crm/<slug>/leads/<id>/	crm/lead_detail.html	Ficha con timeline, selector etapa, notas, resumen IA, fuente del lead, botón eliminar
TrashView	/crm/<slug>/trash/	crm/trash.html	Tabla de leads eliminados con botón restaurar
AnalyticsView	/crm/<slug>/analytics/	crm/analytics.html	Dashboard de métricas con gráfico de embudo, torta por fuente, leads en el tiempo, filtros
Sistema modular de plantillas
crm/base.html: Estructura HTML principal, carga de CSS/JS globales, incluye header.html, navbar.html, sidebar.html (opcional), footer.html. Define bloques content, extra_css, extra_js.

crm/header.html: Logo, nombre del tenant, avatar con dropdown (Configuración, Papelera, Cerrar sesión), theme toggle. Recibe tenant.

crm/navbar.html: Navegación principal (Dashboard, Analíticas, Papelera). Recibe active_page.

crm/sidebar.html: Filtros avanzados para el Kanban/analíticas. Se incluye solo en páginas que lo requieran (show_sidebar=True). Recibe filters.

crm/footer.html: Copyright y versión del sistema.

Funcionalidades de UI
Dashboard Kanban
Drag & drop con modales: nota opcional al mover, modal "error vs recompra" al mover desde etapa cerrada.

Cada tarjeta muestra nombre, teléfono, producto, tiempo desde última actividad y color de la etapa.

Botón de eliminar (icono papelera) en cada tarjeta, con confirmación modal.

Buscador en tiempo real que filtra tarjetas y actualiza contadores.

Estadísticas superiores: total leads, nuevos hoy, en proceso, ganados.

Widget "Leads que necesitan atención hoy" (desde DailyFollowupReport), colapsable, encima del Kanban.

Ficha de Lead
Timeline de actividades con performed_by visible.

Selector de etapa y botón eliminar.

Área de notas con widgets de actividades recientes.

Sección de resumen IA del contacto.

Sección "Origen del lead" con plataforma, UTMs, landing page y referido.

Papelera
Tabla de leads eliminados (contacto, producto, fecha, eliminado por).

Botón restaurar con llamada al endpoint restore.

Dashboard de Analíticas
Gráfico de embudo (barra horizontal) por etapa.

Gráfico de torta de leads por fuente.

Gráfico de líneas/barras de leads en el tiempo.

Filtros: rango de fechas (7d, 30d, 90d), fuente.

Stats cards: total leads, tasa de conversión, tiempo promedio de cierre.

Los gráficos responden al cambio de tema (oscuro/claro).

Tema Claro/Oscuro
Variables CSS en crm/static/crm/css/themes.css.

Toggle en header con icono sol/luna.

Persistencia en localStorage.

Reporte Diario de Seguimiento
Celery genera un DailyFollowupReport a las 9:00 AM y 5:00 PM.

El dashboard muestra el widget con los leads no contactados en 24h.

El usuario puede marcar el reporte como leído.

Tareas Celery
daily_followup_report: 9:00 AM y 5:00 PM, genera reporte de leads sin seguimiento.

auto_advance_stage: cada 4 horas, avanza leads estancados (>48h en etapa no cerrada).

permanently_delete_old_leads: diario a las 3 AM, elimina definitivamente leads con deleted_at > 30 días.

Estructura de archivos
text
crm/
├── domain/
│   ├── models.py
│   ├── services.py
│   └── contact_sync.py
├── interfaces/
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
├── infrastructure/
│   └── tasks.py
├── templates/crm/
│   ├── base.html
│   ├── header.html
│   ├── navbar.html
│   ├── sidebar.html
│   ├── footer.html
│   ├── dashboard.html
│   ├── lead_detail.html
│   ├── trash.html
│   └── analytics.html
├── static/crm/
│   ├── css/
│   │   ├── dashboard.css
│   │   └── themes.css
│   └── js/
│       └── dashboard.js
├── management/commands/
│   └── seed_solar_client.py
└── tests/
    ├── test_views.py
    └── test_services.py