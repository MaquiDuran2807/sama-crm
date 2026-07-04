"""Factory Boy factories for the tenants app.

Each factory provides a convenient way to generate model instances
for use in tests, following the same data shape as the conftest.py fixtures.
"""

import factory
from factory.django import DjangoModelFactory
from tenants.domain.models import Tenant, TenantModule, PipelineConfig, CustomField, TenantUser, SubscriptionTier, SubscriptionPeriod


class TenantFactory(DjangoModelFactory):
    class Meta:
        model = Tenant
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Test Tenant {n}")
    slug = factory.Sequence(lambda n: f"test-tenant-{n}")
    is_active = True
    blueprint = {}
    tier = SubscriptionTier.BASICO.value
    period = SubscriptionPeriod.QUARTERLY.value
    auto_renew = True


class PipelineConfigFactory(DjangoModelFactory):
    class Meta:
        model = PipelineConfig

    tenant = factory.SubFactory(TenantFactory)
    stages = [
        {"name": "Lead", "color": "#003366", "order": 1},
        {"name": "Calificacion", "color": "#FF9933", "order": 2},
        {"name": "Propuesta", "color": "#3366FF", "order": 3},
        {"name": "Negociacion", "color": "#FF33CC", "order": 4},
        {"name": "Cerrado Ganado", "color": "#00CC66", "order": 5, "is_closed": True},
        {"name": "Cerrado Perdido", "color": "#CC0000", "order": 6, "is_closed": True},
    ]
    allow_skip_stages = True


class TenantModuleFactory(DjangoModelFactory):
    class Meta:
        model = TenantModule

    tenant = factory.SubFactory(TenantFactory)
    module_key = factory.Sequence(lambda n: f"module-{n}")
    display_name = factory.Faker("word")
    is_active = True
    config = {}


class CustomFieldFactory(DjangoModelFactory):
    class Meta:
        model = CustomField

    tenant = factory.SubFactory(TenantFactory)
    target_model = "contact"
    field_name = factory.Sequence(lambda n: f"custom_field_{n}")
    field_type = "text"
    options = []
    is_required = False
    order = 0


class TenantUserFactory(DjangoModelFactory):
    class Meta:
        model = TenantUser

    user = factory.SubFactory("auth.tests.factories.UserFactory")
    tenant = factory.SubFactory(TenantFactory)
    role = "member"
