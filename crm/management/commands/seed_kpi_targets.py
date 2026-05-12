"""Command to create test KPI targets for demo tenants."""

from django.core.management.base import BaseCommand
from tenants.domain.models import Tenant
from crm.domain.models import KpiTarget


class Command(BaseCommand):
    help = "Create test KPI targets for all active tenants"

    def handle(self, *args, **options):
        for tenant in Tenant.objects.filter(is_active=True):
            created = 0

            lead_target, _ = KpiTarget.objects.get_or_create(
                tenant=tenant,
                metric_type=KpiTarget.MetricType.LEADS,
                period_type=KpiTarget.PeriodType.MONTHLY,
                defaults={
                    "name": "Leads mensuales",
                    "target_value": 100.0,
                    "is_active": True,
                },
            )
            if lead_target:
                created += 1

            conv_target, _ = KpiTarget.objects.get_or_create(
                tenant=tenant,
                metric_type=KpiTarget.MetricType.CONVERSIONS,
                period_type=KpiTarget.PeriodType.MONTHLY,
                defaults={
                    "name": "Conversiones mensuales",
                    "target_value": 20.0,
                    "is_active": True,
                },
            )
            if conv_target:
                created += 1

            rate_target, _ = KpiTarget.objects.get_or_create(
                tenant=tenant,
                metric_type=KpiTarget.MetricType.CONVERSION_RATE,
                period_type=KpiTarget.PeriodType.MONTHLY,
                defaults={
                    "name": "Tasa de conversion",
                    "target_value": 25.0,
                    "is_active": True,
                },
            )
            if rate_target:
                created += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"[{tenant.name}] {created} KPI targets created/verified"
                )
            )