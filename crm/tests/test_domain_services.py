"""Tests directos para crm/domain/services.py."""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from crm.domain.models import Lead, LeadActivity
from crm.domain.services import (
    change_lead_stage,
    auto_advance_eligible_leads,
    _next_available_stage,
    create_reopen_lead,
    get_lead_summary,
    get_leads_stats,
)
from ingesta.models import ChatUser, DailyTextSummary


class TestChangeLeadStage:
    def test_normal_change_creates_activity(self, db, lead_in_lead):
        lead = change_lead_stage(lead_in_lead, "Propuesta", performed_by="test")
        assert lead.current_stage == "Propuesta"
        assert LeadActivity.objects.filter(
            lead=lead, activity_type="stage_change"
        ).exists()

    def test_change_to_closed_marks_is_closed(self, db, pipeline, lead_in_lead):
        """Cambio a etapa cerrada marca is_closed=True (lógica en use_case)."""
        lead = change_lead_stage(lead_in_lead, "Cerrado Ganado", performed_by="test")
        assert lead.current_stage == "Cerrado Ganado"

    def test_same_stage_is_idempotent(self, db, lead_in_lead):
        """Mismo stage actualiza last_contacted_at y crea actividad."""
        old_ts = lead_in_lead.last_contacted_at
        lead = change_lead_stage(lead_in_lead, "Lead", performed_by="test")
        assert lead.current_stage == "Lead"
        assert lead.last_contacted_at != old_ts
        assert LeadActivity.objects.filter(lead=lead, activity_type="stage_change").count() >= 1

    def test_updates_last_contacted_at(self, db, lead_in_lead):
        old_ts = lead_in_lead.last_contacted_at
        lead = change_lead_stage(lead_in_lead, "Propuesta", performed_by="test")
        assert lead.last_contacted_at != old_ts
        assert lead.last_contacted_at is not None


class TestAutoAdvanceEligibleLeads:
    def test_stale_lead_advances(self, db, tenant, contact, pipeline):
        lead = Lead.objects.create(
            tenant=tenant, contact=contact, current_stage="Lead",
            last_contacted_at=timezone.now() - timedelta(hours=72),
        )
        advanced = auto_advance_eligible_leads(tenant)
        lead.refresh_from_db()
        assert lead.pk in [l.pk for l in advanced]
        assert LeadActivity.objects.filter(lead=lead, activity_type="stage_change").exists()

    def test_recent_lead_does_not_advance(self, db, tenant, contact, pipeline):
        lead = Lead.objects.create(
            tenant=tenant, contact=contact, current_stage="Lead",
            last_contacted_at=timezone.now() - timedelta(hours=1),
        )
        advanced = auto_advance_eligible_leads(tenant)
        assert advanced.count() == 0

    def test_respects_skip_allowed(self, db, tenant, contact, pipeline):
        lead = Lead.objects.create(
            tenant=tenant, contact=contact, current_stage="Lead",
            last_contacted_at=timezone.now() - timedelta(hours=72),
        )
        advanced = auto_advance_eligible_leads(tenant)
        lead.refresh_from_db()
        # Saltando Calificacion (skip_allowed=True), debería ir a Propuesta
        assert lead.current_stage != "Calificacion"

    def test_lead_in_last_stage_not_advanced(self, db, tenant, contact, pipeline):
        lead = Lead.objects.create(
            tenant=tenant, contact=contact, current_stage="Cerrado Ganado",
            is_closed=True,
        )
        advanced = auto_advance_eligible_leads(tenant)
        assert advanced.count() == 0

    def test_no_pipeline_returns_empty(self, db, tenant):
        advanced = auto_advance_eligible_leads(tenant)
        assert advanced.count() == 0

    def test_creates_lead_activity_per_advance(self, db, tenant, contact, pipeline):
        lead = Lead.objects.create(
            tenant=tenant, contact=contact, current_stage="Lead",
            last_contacted_at=timezone.now() - timedelta(hours=72),
        )
        auto_advance_eligible_leads(tenant)
        activities = LeadActivity.objects.filter(lead=lead, activity_type="stage_change")
        assert activities.count() == 1


class TestNextAvailableStage:
    def test_finds_next_stage(self):
        stages = [
            {"name": "Lead", "order": 1},
            {"name": "Calificacion", "order": 2},
            {"name": "Cerrado Ganado", "order": 3},
        ]
        assert _next_available_stage("Lead", stages) == "Calificacion"

    def test_skips_marked_stages(self):
        stages = [
            {"name": "Lead", "order": 1},
            {"name": "Calificacion", "order": 2, "skip_allowed": True},
            {"name": "Propuesta", "order": 3},
        ]
        assert _next_available_stage("Lead", stages) == "Propuesta"

    def test_returns_none_at_last_stage(self):
        stages = [
            {"name": "Lead", "order": 1},
            {"name": "Cerrado Ganado", "order": 2},
        ]
        assert _next_available_stage("Cerrado Ganado", stages) is None

    def test_returns_none_for_unknown_stage(self):
        stages = [{"name": "Lead", "order": 1}]
        assert _next_available_stage("Unknown", stages) is None

    def test_consecutive_skips(self):
        stages = [
            {"name": "Lead", "order": 1},
            {"name": "Skip1", "order": 2, "skip_allowed": True},
            {"name": "Skip2", "order": 3, "skip_allowed": True},
            {"name": "Final", "order": 4},
        ]
        assert _next_available_stage("Lead", stages) == "Final"

    def test_all_skips_returns_none(self):
        stages = [
            {"name": "A", "order": 1},
            {"name": "B", "order": 2, "skip_allowed": True},
        ]
        assert _next_available_stage("A", stages) is None


class TestCreateReopenLead:
    def test_creates_lead_with_is_recompra(self, db, lead_closed_won):
        new_lead = create_reopen_lead(lead_closed_won, "Lead", performed_by="test")
        assert new_lead.is_recompra is True
        assert new_lead.current_stage == "Lead"
        assert new_lead.contact == lead_closed_won.contact

    def test_original_lead_stays_closed(self, db, lead_closed_won):
        create_reopen_lead(lead_closed_won, "Lead", performed_by="test")
        lead_closed_won.refresh_from_db()
        assert lead_closed_won.is_closed is True

    def test_creates_activity(self, db, lead_closed_won):
        new_lead = create_reopen_lead(lead_closed_won, "Lead", performed_by="test")
        assert LeadActivity.objects.filter(
            lead=new_lead, activity_type="recompra"
        ).exists()

    def test_copies_contact_and_product(self, db, lead_closed_won):
        lead_closed_won.product_of_interest = "Panel Solar"
        lead_closed_won.save()
        new_lead = create_reopen_lead(lead_closed_won, "Lead", performed_by="test")
        assert new_lead.product_of_interest == "Panel Solar"
        assert new_lead.contact_id == lead_closed_won.contact_id

    def test_tenant_is_preserved(self, db, lead_closed_won):
        new_lead = create_reopen_lead(lead_closed_won, "Lead", performed_by="test")
        assert new_lead.tenant_id == lead_closed_won.tenant_id


class TestGetLeadSummary:
    def test_returns_summary_when_exists(self, db, lead_in_lead, contact):
        chat_user = ChatUser.objects.create(
            wa_id="573001234567",
            phone_number="573001234567",
            name="Juan Perez",
        )
        summary = DailyTextSummary.objects.create(
            user=chat_user,
            summary_date=timezone.now().date(),
            text="Resumen de prueba",
            has_data=True,
        )
        result = get_lead_summary(lead_in_lead)
        assert result == summary

    def test_returns_none_when_no_chat_user(self, db, tenant, pipeline, contact2):
        cache.clear()
        from crm.domain.models import Contact, Lead
        lead = Lead.objects.create(tenant=tenant, contact=contact2, current_stage="Lead")
        result = get_lead_summary(lead)
        assert result is None

    def test_returns_none_when_no_phone(self, db, tenant, pipeline):
        from crm.domain.models import Contact
        c = Contact.objects.create(tenant=tenant, full_name="No Phone")
        lead = Lead.objects.create(tenant=tenant, contact=c, current_stage="Lead")
        result = get_lead_summary(lead)
        assert result is None

    def test_uses_cache(self, db, lead_in_lead, contact):
        chat_user = ChatUser.objects.create(
            wa_id="573001234567", phone_number="573001234567",
        )
        DailyTextSummary.objects.create(
            user=chat_user, summary_date=timezone.now().date(),
            text="Cached", has_data=True,
        )
        from django.core.cache import cache
        cache.clear()
        result1 = get_lead_summary(lead_in_lead)
        result2 = get_lead_summary(lead_in_lead)
        assert result1 == result2


class TestGetLeadsStats:
    def test_counts_total_leads(self, db, tenant, pipeline, lead_in_lead, lead_in_calificacion):
        stats = get_leads_stats(tenant)
        assert stats["total_leads"] >= 2

    def test_counts_active_leads(self, db, tenant, pipeline, lead_in_lead, lead_closed_won):
        stats = get_leads_stats(tenant)
        assert stats["active_leads"] == 1

    def test_counts_won_leads(self, db, tenant, pipeline, lead_closed_won):
        stats = get_leads_stats(tenant)
        assert stats["won_leads"] == 1

    def test_leads_by_stage(self, db, tenant, pipeline, lead_in_lead, lead_in_calificacion):
        stats = get_leads_stats(tenant)
        assert "Lead" in stats["leads_por_etapa"]
        assert stats["leads_por_etapa"]["Lead"] >= 1

    def test_empty_tenant_returns_zeros(self, db, tenant):
        stats = get_leads_stats(tenant)
        assert stats["total_leads"] == 0
        assert stats["active_leads"] == 0
        assert stats["won_leads"] == 0
        assert stats["leads_por_etapa"] == {}
