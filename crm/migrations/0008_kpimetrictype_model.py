from django.db import migrations, models


METRIC_DEFAULTS = [
    ("leads", "Leads totales", "Total de nuevos leads captados", "leads", "bi-people", "#3b82f6", "volume", 1),
    ("conversions", "Conversiones", "Leads cerrados como ganados", "leads", "bi-trophy", "#2ec27e", "conversion", 2),
    ("conversion_rate", "Tasa de conversion", "Porcentaje de leads convertidos", "%", "bi-graph-up", "#8b5cf6", "conversion", 3),
    ("avg_days", "Dias promedio cierre", "Tiempo promedio en dias para cerrar un lead", "dias", "bi-clock", "#f5a623", "efficiency", 4),
    ("avg_deal_value", "Valor promedio negocio", "Valor promedio por negocio cerrado", "COP", "bi-currency-dollar", "#06b6d4", "revenue", 5),
    ("revenue", "Ingresos totales", "Suma de valores de negocios cerrados", "COP", "bi-wallet2", "#22c55e", "revenue", 6),
    ("quotes_sent", "Cotizaciones enviadas", "Total de cotizaciones enviadas a clientes", "cotiz.", "bi-file-earmark-text", "#f59e0b", "volume", 7),
    ("quotes_accepted", "Cotizaciones aceptadas", "Cotizaciones aceptadas por el cliente", "cotiz.", "bi-check-square", "#10b981", "conversion", 8),
    ("leads_per_day", "Leads por dia", "Promedio de leads captados por dia", "leads/dia", "bi-calendar-day", "#6366f1", "efficiency", 9),
    ("pipeline_value", "Valor en pipeline", "Suma de valores de leads activos en pipeline", "COP", "bi-stack", "#0ea5e9", "revenue", 10),
    ("retention_rate", "Tasa de retencion", "Porcentaje de clientes que repiten compra", "%", "bi-person-check", "#a855f7", "conversion", 11),
    ("follow_up_rate", "Tasa de seguimiento", "Porcentaje de leads con seguimiento realizado", "%", "bi-chat-left-text", "#ec4899", "efficiency", 12),
    ("new_contacts", "Contactos nuevos", "Total de contactos nuevos creados", "contactos", "bi-person-plus", "#14b8a6", "volume", 13),
    ("emails_sent", "Emails enviados", "Campanas de email enviadas", "emails", "bi-envelope", "#64748b", "volume", 14),
    ("calls_made", "Llamadas realizadas", "Total de llamadas telefonicas realizadas", "llamadas", "bi-telephone", "#0d9488", "volume", 15),
    ("meetings_scheduled", "Reuniones agendadas", "Reuniones programadas con clientes", "reuniones", "bi-calendar-event", "#7c3aed", "volume", 16),
    ("cost_per_lead", "Costo por lead", "Costo promedio de adquisicion por lead", "COP", "bi-cash-stack", "#b45309", "efficiency", 17),
    ("roi", "Retorno de inversion", "ROI de las campanhas de adquisicion", "%", "bi-bar-chart", "#059669", "revenue", 18),
]


def seed_metric_types(apps, schema_editor):
    KpiMetricType = apps.get_model('crm', 'KpiMetricType')
    for slug, name, desc, unit, icon, color, cat, order in METRIC_DEFAULTS:
        KpiMetricType.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name, 'description': desc, 'unit': unit,
                'icon': icon, 'color': color, 'category': cat, 'sort_order': order,
            }
        )


def seed_metric_types_reverse(apps, schema_editor):
    KpiMetricType = apps.get_model('crm', 'KpiMetricType')
    KpiMetricType.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0007_kpitarget'),
    ]

    operations = [
        migrations.CreateModel(
            name='KpiMetricType',
            fields=[
                ('slug', models.SlugField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('unit', models.CharField(max_length=30)),
                ('icon', models.CharField(max_length=50)),
                ('color', models.CharField(max_length=7)),
                ('category', models.CharField(max_length=50)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.RunPython(seed_metric_types, seed_metric_types_reverse),
        migrations.AddField(
            model_name='kpitarget',
            name='metric',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name='kpi_targets',
                to='crm.KpiMetricType',
            ),
        ),
    ]