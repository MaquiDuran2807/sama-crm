"""Command to create test KPI targets for demo tenants using KpiMetricType."""

from django.core.management.base import BaseCommand
from tenants.domain.models import Tenant
from crm.domain.models import KpiTarget, KpiMetricType


class Command(BaseCommand):
    help = "Create test KPI targets for all active tenants"

    def handle(self, *args, **options):
        for tenant in Tenant.objects.filter(is_active=True):
            created = 0

            for slug, target_value in [
                ("leads", 100.0),
                ("conversions", 20.0),
                ("conversion_rate", 25.0),
            ]:
                metric = KpiMetricType.objects.filter(slug=slug).first()
                if not metric:
                    self.stdout.write(self.style.WARNING(f"[{tenant.name}] Metric '{slug}' not found, skipping"))
                    continue

                target, is_new = KpiTarget.objects.get_or_create(
                    tenant=tenant,
                    metric=metric,
                    period_type="monthly",
                    defaults={"target_value": target_value, "is_active": True},
                )
                if is_new:
                    created += 1

            self.stdout.write(
                self.style.SUCCESS(f"[{tenant.name}] {created} KPI targets created/verified")
            )