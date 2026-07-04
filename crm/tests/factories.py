"""Factory Boy factories for the CRM app.

Provides factories for Contact, Lead, LeadSource, Tag, LeadTag,
LeadActivity, LeadTask, Product, LeadProduct, KpiMetricType, and KpiTarget.
"""

import random
from datetime import timedelta

import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from crm.domain.models import (
    Contact, Lead, LeadSource, LeadActivity,
    Tag, LeadTag, LeadTask,
    Product, LeadProduct,
    KpiMetricType, KpiTarget,
)


class ContactFactory(DjangoModelFactory):
    class Meta:
        model = Contact

    tenant = factory.SubFactory("tenants.tests.factories.TenantFactory")
    full_name = factory.Faker("name")
    phone_number = factory.Sequence(lambda n: f"57{n:010d}")
    email = factory.Faker("email")
    address = factory.Faker("address")
    utm_source = ""
    utm_medium = ""
    utm_campaign = ""
    custom_fields = {}


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    tenant = factory.SubFactory("tenants.tests.factories.TenantFactory")
    name = factory.Sequence(lambda n: f"Product {n}")
    sku = factory.Sequence(lambda n: f"SKU-{n:04d}")
    price = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    is_active = True


class LeadFactory(DjangoModelFactory):
    class Meta:
        model = Lead
        skip_postgeneration_save = True

    tenant = factory.SubFactory("tenants.tests.factories.TenantFactory")
    contact = factory.SubFactory(ContactFactory)
    current_stage = "Lead"
    product_of_interest = ""
    product_category = ""
    notes = ""
    skipped_stages = []
    is_closed = False
    closed_result = ""
    is_recompra = False
    deal_value = None
    custom_fields = {}
    is_deleted = False

    @factory.post_generation
    def ensure_pipeline(obj, create, extracted, **kwargs):
        if not create:
            return
        from tenants.domain.models import PipelineConfig
        PipelineConfig.objects.get_or_create(
            tenant=obj.tenant,
            defaults={
                "stages": [
                    {"name": "Lead", "color": "#003366", "order": 1},
                    {"name": "Cerrado Ganado", "color": "#00CC66", "order": 2, "is_closed": True},
                    {"name": "Cerrado Perdido", "color": "#CC0000", "order": 3, "is_closed": True},
                ],
            },
        )


class LeadSourceFactory(DjangoModelFactory):
    class Meta:
        model = LeadSource

    lead = factory.SubFactory(LeadFactory)
    platform = factory.LazyFunction(lambda: random.choice(["web", "meta", "google", "tiktok", "referral"]))
    utm_source = ""
    utm_medium = ""
    utm_campaign = ""
    landing_page_url = ""


class TagFactory(DjangoModelFactory):
    class Meta:
        model = Tag
        django_get_or_create = ("tenant", "name")

    tenant = factory.SubFactory("tenants.tests.factories.TenantFactory")
    name = factory.Sequence(lambda n: f"Tag {n}")
    color = factory.Faker("hex_color")
    is_predefined = False


class LeadTagFactory(DjangoModelFactory):
    class Meta:
        model = LeadTag

    lead = factory.SubFactory(LeadFactory)
    tag = factory.SubFactory(TagFactory)


class LeadActivityFactory(DjangoModelFactory):
    class Meta:
        model = LeadActivity

    lead = factory.SubFactory(LeadFactory)
    activity_type = factory.Faker("word")
    description = factory.Faker("sentence")
    performed_by = "system"
    created_at = factory.LazyFunction(timezone.now)


class LeadTaskFactory(DjangoModelFactory):
    class Meta:
        model = LeadTask

    lead = factory.SubFactory(LeadFactory)
    description = factory.Faker("sentence")
    due_date = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    is_completed = False
    completed_at = None


class KpiMetricTypeFactory(DjangoModelFactory):
    class Meta:
        model = KpiMetricType
        django_get_or_create = ("slug",)

    slug = factory.Sequence(lambda n: f"metric-{n}")
    name = factory.Sequence(lambda n: f"Metric {n}")
    description = ""
    unit = "leads"
    icon = "bi-people"
    color = "#3b82f6"
    category = "volume"
    sort_order = 0
    is_active = True


class KpiTargetFactory(DjangoModelFactory):
    class Meta:
        model = KpiTarget

    tenant = factory.SubFactory("tenants.tests.factories.TenantFactory")
    metric = factory.SubFactory(KpiMetricTypeFactory)
    target_value = 100.0
    period_type = KpiTarget.PeriodType.MONTHLY.value
    is_active = True


class LeadProductFactory(DjangoModelFactory):
    class Meta:
        model = LeadProduct

    lead = factory.SubFactory(LeadFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1
    notes = ""
