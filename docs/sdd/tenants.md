# SDD — App tenants

## Propósito
Gestiona los clientes de SAMA (tenants), sus suscripciones, módulos activos, pipelines de ventas configurables y campos personalizados para el CRM.

## Modelos

### Tenant
- **id** (PK, autogenerado)
- **name**: CharField(255)
- **slug**: SlugField(unique)
- **is_active**: BooleanField(default=True)
- **blueprint**: JSONField(default=dict) — configuración general
- **tier**: CharField(choices=SubscriptionTier) — basico/pro/full
- **period**: CharField(choices=SubscriptionPeriod) — monthly/quarterly
- **subscription_start**: DateField(null=True)
- **subscription_end**: DateField(null=True)
- **auto_renew**: BooleanField(default=True)
- **created_at**, **updated_at**: DateTimeField

### TenantModule
- **id** (PK)
- **tenant**: FK Tenant (CASCADE, related_name="modules")
- **module_key**: CharField(100)
- **display_name**: CharField(255, blank=True)
- **is_active**: BooleanField(default=True)
- **config**: JSONField(default=dict)
- **created_at**: DateTimeField
- **unique_together**: [tenant, module_key]

### PipelineConfig
- **id** (PK)
- **tenant**: OneToOneField Tenant (CASCADE, related_name="pipeline_config")
- **stages**: JSONField(default=list) — [{name, color, order}]
- **allow_skip_stages**: BooleanField(default=True)

### CustomField
- **id** (PK)
- **tenant**: FK Tenant (CASCADE, related_name="custom_fields")
- **target_model**: CharField(choices=TargetModel) — contact/lead
- **field_name**: CharField(100)
- **field_type**: CharField(choices=FieldType) — text/number/date/select
- **options**: JSONField(default=list) — opciones si es select
- **is_required**: BooleanField(default=False)
- **order**: PositiveIntegerField(default=0)

### Choices
- **SubscriptionTier**: BASICO, PRO, FULL
- **SubscriptionPeriod**: MONTHLY, QUARTERLY
- **TargetModel**: CONTACT, LEAD
- **FieldType**: TEXT, NUMBER, DATE, SELECT

## Servicios de dominio (domain/services.py)
- `is_subscription_active(tenant) -> bool`: verifica que la fecha actual esté dentro del rango de suscripción.
- `get_pipeline_stages(tenant) -> list`: devuelve las etapas ordenadas.
- `get_active_modules(tenant) -> QuerySet`: devuelve los TenantModule con is_active=True.
- `get_custom_fields(tenant, target_model) -> QuerySet`: devuelve campos filtrados.

## Endpoints REST
- `GET /api/tenants/` — lista tenants activos.
- `GET /api/tenants/{slug}/` — detalle de tenant.
- `GET /api/tenants/{slug}/pipeline/` — etapas del pipeline.
- `GET /api/tenants/{slug}/modules/` — módulos activos.
- `GET /api/tenants/{slug}/custom-fields/?target_model=contact|lead` — campos personalizados.