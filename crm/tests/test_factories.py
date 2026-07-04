"""Tests to verify that all factories generate valid model instances."""

import pytest

from tenants.tests.factories import TenantFactory, PipelineConfigFactory, TenantModuleFactory, CustomFieldFactory
from auth.tests.factories import UserFactory
from ingesta.tests.factories import EvolutionInstanceFactory, ChatUserFactory, MessageFactory, DailyTextSummaryFactory
from crm.tests.factories import (
    ContactFactory, LeadFactory, LeadSourceFactory, TagFactory,
    LeadActivityFactory, LeadTaskFactory, ProductFactory,
    KpiMetricTypeFactory, KpiTargetFactory,
)


@pytest.mark.django_db
class TestTenantsFactories:
    def test_tenant_factory(self):
        tenant = TenantFactory()
        assert tenant.pk
        assert tenant.is_active
        assert tenant.slug.startswith("test-tenant")

    def test_pipeline_config_factory(self):
        pipeline = PipelineConfigFactory()
        assert pipeline.pk
        assert len(pipeline.stages) > 0

    def test_tenant_module_factory(self):
        module = TenantModuleFactory()
        assert module.pk
        assert module.is_active

    def test_custom_field_factory(self):
        field = CustomFieldFactory()
        assert field.pk
        assert field.target_model == "contact"


@pytest.mark.django_db
class TestAuthFactories:
    def test_user_factory(self):
        user = UserFactory()
        assert user.pk
        assert user.check_password("testpass123")
        assert user.username.startswith("user_")

    def test_user_factory_unique_usernames(self):
        user1 = UserFactory()
        user2 = UserFactory()
        assert user1.username != user2.username


@pytest.mark.django_db
class TestIngestaFactories:
    def test_evolution_instance_factory(self):
        instance = EvolutionInstanceFactory()
        assert instance.pk
        assert instance.is_active

    def test_chat_user_factory(self):
        user = ChatUserFactory()
        assert user.pk
        assert user.wa_id.endswith("@c.us")

    def test_message_factory(self):
        msg = MessageFactory()
        assert msg.pk
        assert msg.external_id.startswith("msg_")

    def test_daily_summary_factory(self):
        summary = DailyTextSummaryFactory()
        assert summary.pk
        assert summary.has_data


@pytest.mark.django_db
class TestCrmFactories:
    def test_contact_factory(self):
        contact = ContactFactory()
        assert contact.pk
        assert contact.full_name

    def test_lead_factory(self):
        lead = LeadFactory()
        assert lead.pk
        assert lead.current_stage == "Lead"
        assert not lead.is_closed

    def test_lead_source_factory(self):
        source = LeadSourceFactory()
        assert source.pk
        assert source.platform in ["web", "meta", "google", "tiktok", "referral"]

    def test_tag_factory(self):
        tag = TagFactory()
        assert tag.pk
        assert tag.name.startswith("Tag")

    def test_lead_activity_factory(self):
        activity = LeadActivityFactory()
        assert activity.pk
        assert activity.description

    def test_lead_task_factory(self):
        task = LeadTaskFactory()
        assert task.pk
        assert not task.is_completed

    def test_product_factory(self):
        product = ProductFactory()
        assert product.pk
        assert product.is_active

    def test_kpi_metric_type_factory(self):
        metric = KpiMetricTypeFactory()
        assert metric.pk
        assert metric.slug.startswith("metric-")

    def test_kpi_target_factory(self):
        target = KpiTargetFactory()
        assert target.pk
        assert target.target_value == 100.0
