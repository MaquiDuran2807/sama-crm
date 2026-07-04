from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from tenants.models import Tenant


class KpiMetricType(models.Model):
    """Definicion de un tipo de metric KPI disponible en la plataforma."""

    slug = models.SlugField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100, help_text="Nombre para mostrar, ej: 'Leads totales'")
    description = models.TextField(blank=True, help_text="Descripcion del metric")
    unit = models.CharField(max_length=30, help_text="Unidad de medida, ej: 'leads', '%', 'dias'")
    icon = models.CharField(max_length=50, help_text="Clase Bootstrap Icon, ej: 'bi-people'")
    color = models.CharField(max_length=7, help_text="Color hex para UI, ej: '#3b82f6'")
    category = models.CharField(max_length=50, help_text="Grupo: 'volume', 'conversion', 'revenue', 'efficiency'")
    sort_order = models.PositiveIntegerField(default=0, help_text="Orden en la UI")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Tipo de Metric KPI"
        verbose_name_plural = "Tipos de Metric KPI"

    def __str__(self):
        return self.name

    @classmethod
    def get_defaults(cls):
        return [
            {"slug": "leads", "name": "Leads totales", "description": "Total de nuevos leads captados", "unit": "leads", "icon": "bi-people", "color": "#3b82f6", "category": "volume", "sort_order": 1},
            {"slug": "conversions", "name": "Conversiones", "description": "Leads cerrados como ganados", "unit": "leads", "icon": "bi-trophy", "color": "#2ec27e", "category": "conversion", "sort_order": 2},
            {"slug": "conversion_rate", "name": "Tasa de conversion", "description": "Porcentaje de leads convertidos", "unit": "%", "icon": "bi-graph-up", "color": "#8b5cf6", "category": "conversion", "sort_order": 3},
            {"slug": "avg_days", "name": "Dias promedio cierre", "description": "Tiempo promedio en dias para cerrar un lead", "unit": "dias", "icon": "bi-clock", "color": "#f5a623", "category": "efficiency", "sort_order": 4},
            {"slug": "avg_deal_value", "name": "Valor promedio negocio", "description": "Valor promedio por negocio cerrado", "unit": "COP", "icon": "bi-currency-dollar", "color": "#06b6d4", "category": "revenue", "sort_order": 5},
            {"slug": "revenue", "name": "Ingresos totales", "description": "Suma de valores de negocios cerrados", "unit": "COP", "icon": "bi-wallet2", "color": "#22c55e", "category": "revenue", "sort_order": 6},
            {"slug": "quotes_sent", "name": "Cotizaciones enviadas", "description": "Total de cotizaciones enviadas a clientes", "unit": "cotiz.", "icon": "bi-file-earmark-text", "color": "#f59e0b", "category": "volume", "sort_order": 7},
            {"slug": "quotes_accepted", "name": "Cotizaciones aceptadas", "description": "Cotizaciones aceptadas por el cliente", "unit": "cotiz.", "icon": "bi-check-square", "color": "#10b981", "category": "conversion", "sort_order": 8},
            {"slug": "leads_per_day", "name": "Leads por dia", "description": "Promedio de leads captados por dia", "unit": "leads/dia", "icon": "bi-calendar-day", "color": "#6366f1", "category": "efficiency", "sort_order": 9},
            {"slug": "pipeline_value", "name": "Valor en pipeline", "description": "Suma de valores de leads activos en pipeline", "unit": "COP", "icon": "bi-stack", "color": "#0ea5e9", "category": "revenue", "sort_order": 10},
            {"slug": "retention_rate", "name": "Tasa de retencion", "description": "Porcentaje de clientes que repiten compra", "unit": "%", "icon": "bi-person-check", "color": "#a855f7", "category": "conversion", "sort_order": 11},
            {"slug": "follow_up_rate", "name": "Tasa de seguimiento", "description": "Porcentaje de leads con seguimiento realizado", "unit": "%", "icon": "bi-chat-left-text", "color": "#ec4899", "category": "efficiency", "sort_order": 12},
            {"slug": "new_contacts", "name": "Contactos nuevos", "description": "Total de contactos nuevos creados", "unit": "contactos", "icon": "bi-person-plus", "color": "#14b8a6", "category": "volume", "sort_order": 13},
            {"slug": "emails_sent", "name": "Emails enviados", "description": "Campanas de email enviadas", "unit": "emails", "icon": "bi-envelope", "color": "#64748b", "category": "volume", "sort_order": 14},
            {"slug": "calls_made", "name": "Llamadas realizadas", "description": "Total de llamadas telefonicas realizadas", "unit": "llamadas", "icon": "bi-telephone", "color": "#0d9488", "category": "volume", "sort_order": 15},
            {"slug": "meetings_scheduled", "name": "Reuniones agendadas", "description": "Reuniones programadas con clientes", "unit": "reuniones", "icon": "bi-calendar-event", "color": "#7c3aed", "category": "volume", "sort_order": 16},
            {"slug": "cost_per_lead", "name": "Costo por lead", "description": "Costo promedio de adquisicion por lead", "unit": "COP", "icon": "bi-cash-stack", "color": "#b45309", "category": "efficiency", "sort_order": 17},
            {"slug": "roi", "name": "Retorno de inversion", "description": "ROI de las campanhas de adquisicion", "unit": "%", "icon": "bi-bar-chart", "color": "#059669", "category": "revenue", "sort_order": 18},
        ]


class Contact(models.Model):
    """Cliente final de un tenant (ej: Juan Pérez)."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="contacts")
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=32, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.ForeignKey("City", on_delete=models.SET_NULL, null=True, blank=True, related_name="contacts")
    region = models.CharField(max_length=100, blank=True)

    # Origen del contacto
    utm_source = models.CharField(max_length=50, blank=True)
    utm_medium = models.CharField(max_length=50, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    referrer_contact = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referred_contacts")

    # Datos personalizados (definidos por el tenant en CustomField)
    custom_fields = models.JSONField(default=dict)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "phone_number"]),
            models.Index(fields=["tenant", "email"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.phone_number or self.email or 'sin contacto'})"


class LeadQuerySet(models.QuerySet):
    """QuerySet personalizado con métodos de consulta para leads."""

    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def closed(self):
        return self.filter(is_closed=True)


class LeadManager(models.Manager.from_queryset(LeadQuerySet)):
    """Manager que expone los métodos de LeadQuerySet (active, deleted, closed)."""


class Lead(models.Model):
    """Oportunidad de venta. Un contacto puede tener varios leads."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="leads")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="leads")
    current_stage = models.CharField(max_length=100)
    product_of_interest = models.CharField(max_length=255, blank=True)
    product_category = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    skipped_stages = models.JSONField(default=list)
    is_closed = models.BooleanField(default=False)
    closed_result = models.CharField(max_length=20, blank=True)
    is_recompra = models.BooleanField(default=False, db_index=True)
    deal_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, default=0,
        help_text="Valor monetario estimado del negocio (COP)"
    )

    custom_fields = models.JSONField(default=dict)

    # ── Soft delete ──
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)

    objects = LeadManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "current_stage"]),
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["contact", "-created_at"]),
            models.Index(fields=["is_deleted"]),
            models.Index(fields=["deleted_at"]),
        ]
        ordering = ["-updated_at"]

    @cached_property
    def computed_value(self) -> float:
        """Valor total del lead: deal_value directo + suma de productos."""
        direct = float(self.deal_value or 0)
        product_sum = sum(
            float(lp.quantity or 1) * float(lp.product.price or 0)
            for lp in self.lead_products.select_related('product').all()
        )
        return direct + product_sum

    def __str__(self):
        return f"Lead {self.id} - {self.contact.full_name} ({self.current_stage})"


class Product(models.Model):
    """Producto o servicio que vende un tenant."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255, help_text="Nombre del producto o servicio")
    sku = models.CharField(max_length=100, blank=True, help_text="Codigo SKU del producto")
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text="Precio estandar del producto (COP)"
    )
    cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Costo de adquisicion del producto (COP)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

    @property
    def margin(self):
        """Margen bruto si se conoce el costo."""
        if self.cost and self.price:
            return float(self.price - self.cost) / float(self.price) * 100 if float(self.price) else 0
        return None


class LeadProduct(models.Model):
    """Relacion many-to-many entre Lead y Product con cantidad."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="lead_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="lead_products")
    quantity = models.PositiveIntegerField(default=1, help_text="Cantidad de unidades")
    unit_price_override = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Precio unitario override (si difiere del precio estandar)"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["lead", "product"]
        verbose_name = "Producto en Lead"
        verbose_name_plural = "Productos en Leads"

    def __str__(self):
        return f"{self.product.name} x{self.quantity} -> Lead {self.lead_id}"

    @property
    def line_total(self) -> float:
        """Valor de la linea: cantidad x precio unitario."""
        price = self.unit_price_override if self.unit_price_override else self.product.price
        return float(self.quantity or 1) * float(price or 0)


class LeadSource(models.Model):
    """Origen del lead con detalle de UTM y plataforma."""
    class Platform(models.TextChoices):
        META = "meta", "Meta (Facebook/Instagram)"
        GOOGLE = "google", "Google Ads"
        TIKTOK = "tiktok", "TikTok"
        WEB = "web", "Página web"
        REFERRAL = "referral", "Referido"

    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name="source")
    platform = models.CharField(max_length=20, choices=Platform.choices, default=Platform.WEB)
    utm_source = models.CharField(max_length=50, blank=True)
    utm_medium = models.CharField(max_length=50, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    referrer_contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL, related_name="referred_leads")
    landing_page_url = models.URLField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    PLATFORM_ICONS = {
        "meta": "bi-facebook",
        "google": "bi-google",
        "tiktok": "bi-tiktok",
        "web": "bi-globe",
        "referral": "bi-person-lines-fill",
    }

    def get_icon_class(self) -> str:
        """Retorna la clase del icono Bootstrap correspondiente a la plataforma."""
        return self.PLATFORM_ICONS.get(self.platform, "bi-globe")

    def __str__(self):
        return f"Fuente de {self.lead}"


class LeadActivity(models.Model):
    """Historial de actividades sobre un lead."""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=50, help_text="stage_change, note_added, auto_advance, etc.")
    description = models.TextField()
    performed_by = models.CharField(max_length=100, default="system")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.activity_type} en {self.lead} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"


class DailyFollowupReport(models.Model):
    """Reporte diario de seguimiento de leads fríos o pendientes."""
    class ReportType(models.TextChoices):
        MANANA = "manana", "Mañana"
        TARDE = "tarde", "Tarde"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="followup_reports")
    report_type = models.CharField(max_length=10, choices=ReportType.choices, default=ReportType.MANANA)
    date = models.DateField()
    target_leads = models.JSONField(default=list, help_text="Lista de lead_ids a seguir")
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-report_type"]
        unique_together = ["tenant", "date", "report_type"]

    def __str__(self):
        return f"Reporte {self.report_type} - {self.date}"
    
class LeadTask(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="tasks")
    description = models.CharField(max_length=255)
    due_date = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Task: {self.description} ({self.lead})"


class Department(models.Model):
    """Departamento geografico para agrupar ciudades."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Departments"
        ordering = ["name"]

    def __str__(self):
        return self.name


class City(models.Model):
    """Ciudad asociada a un departamento."""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="cities")
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        unique_together = ["department", "name"]
        ordering = ["department__name", "name"]

    def __str__(self):
        return f"{self.name}, {self.department.name}"


class Tag(models.Model):
    """Etiqueta para categorizar leads."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#3498db")
    is_predefined = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ["tenant", "name"]
        ordering = ["name"]

    def __str__(self):
        return f"{self.tenant.name} / {self.name}"


class KpiTarget(models.Model):
    """Meta de KPI para un tenant — vinculada a un KpiMetricType."""

    class PeriodType(models.TextChoices):
        DAILY = "daily", "Diario"
        WEEKLY = "weekly", "Semanal"
        MONTHLY = "monthly", "Mensual"
        QUARTERLY = "quarterly", "Trimestral"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="kpi_targets")
    metric = models.ForeignKey(KpiMetricType, on_delete=models.CASCADE, related_name="kpi_targets")
    target_value = models.FloatField(help_text="Valor objetivo")
    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.MONTHLY)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["metric__sort_order", "period_type"]
        unique_together = ["tenant", "metric", "period_type"]

    def __str__(self):
        return f"{self.metric.name} - {self.target_value} ({self.tenant.name})"

    @property
    def metric_type(self):
        return self.metric.slug if self.metric else ""

    @property
    def name(self):
        return self.metric.name if self.metric else ""

    @property
    def unit(self):
        return self.metric.unit if self.metric else ""

    @property
    def icon(self):
        return self.metric.icon if self.metric else ""

    @property
    def color(self):
        return self.metric.color if self.metric else ""

    @property
    def category(self):
        return self.metric.category if self.metric else ""


class LeadTag(models.Model):
    """Relacion many-to-many entre Lead y Tag."""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="lead_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="lead_tags")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ["lead", "tag"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Lead {self.lead_id} - Tag {self.tag_id}"