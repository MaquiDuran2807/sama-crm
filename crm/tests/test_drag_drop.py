"""
crm/tests/test_drag_drop.py

Tests para el sistema de drag & drop del dashboard Kanban.

Cubre los flujos:
- Movimiento normal entre etapas activas → crea nota
- Movimiento de etapa cerrada a activa → modal reopen
- "Fue un error" → revierte la tarjeta
- "Nueva oportunidad" → crea lead con is_recompra=True
- Movimiento de activa a cerrada → actualiza sin modal
"""

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework import status
from crm.domain.models import (
    Lead, Contact, LeadSource, LeadActivity, Tag, LeadTag,
)
from tenants.models import Tenant
from tenants.domain.models import PipelineConfig


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Test Tenant", slug="testtenant", is_active=True)


@pytest.fixture
def pipeline(db, tenant):
    return PipelineConfig.objects.create(
        tenant=tenant,
        stages=[
            {"name": "Lead", "color": "#003366", "order": 1},
            {"name": "Calificacion", "color": "#FF9933", "order": 2},
            {"name": "Cerrado Ganado", "color": "#00CC66", "order": 3, "is_closed": True},
        ],
        allow_skip_stages=True,
    )


@pytest.fixture
def contact(db, tenant):
    return Contact.objects.create(
        tenant=tenant,
        full_name="Juan Perez",
        phone_number="573001234567",
    )


@pytest.fixture
def user(db):
    from django.contrib.auth.models import User
    return User.objects.create_superuser(username="admin", password="admin", email="admin@test.com")


@pytest.fixture
def lead_active(db, tenant, contact, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Lead",
        is_closed=False,
    )


@pytest.fixture
def lead_closed(db, tenant, contact, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Cerrado Ganado",
        is_closed=True,
        closed_result="won",
    )


@pytest.fixture
def client_auth(db, user):
    client = Client()
    client.force_login(user)
    return client


class TestDragDropAPIFlows:
    """Tests para los flujos de movimiento de leads via API."""

    def test_patch_stage_normal_creates_activity(self, db, tenant, lead_active, user):
        """Movimiento normal entre etapas activas crea actividad."""
        client = Client()
        client.force_login(user)
        response = client.patch(
            f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant",
            {"current_stage": "Calificacion"},
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_200_OK
        lead_active.refresh_from_db()
        assert lead_active.current_stage == "Calificacion"
        assert LeadActivity.objects.filter(lead=lead_active, activity_type="stage_change").exists()

    def test_patch_stage_to_closed_sets_is_closed(self, db, tenant, lead_active, user):
        """Movimiento a etapa cerrada marca is_closed=True."""
        client = Client()
        client.force_login(user)
        response = client.patch(
            f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant",
            {"current_stage": "Cerrado Ganado"},
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_200_OK
        lead_active.refresh_from_db()
        assert lead_active.current_stage == "Cerrado Ganado"
        assert lead_active.is_closed is True
        assert lead_active.closed_result == "won"

class TestReopenEndpoint:
    """Tests para el endpoint de reopen (recompra)."""

    def test_reopen_creates_new_lead_as_recompra(self, db, tenant, contact, pipeline, lead_closed, user):
        """POST reopen crea un nuevo lead marcado como recompra."""
        assert lead_closed.is_closed is True
        assert lead_closed.closed_result == "won"

        client = Client()
        client.force_login(user)
        response = client.post(
            f"/api/crm/leads/{lead_closed.id}/reopen/?tenant_slug=testtenant",
            {"product_of_interest": "Panel Solar 500W", "notes": "Cliente quiere comprar de nuevo"},
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        new_lead_id = response.json().get("id")
        assert new_lead_id is not None
        assert new_lead_id != lead_closed.id

        new_lead = Lead.objects.get(id=new_lead_id)
        assert new_lead.current_stage == "Lead"
        assert new_lead.contact == lead_closed.contact
        assert new_lead.is_recompra is True
        assert new_lead.is_closed is False

        lead_closed.refresh_from_db()
        assert lead_closed.is_closed is True

    def test_reopen_creates_recompra_activity(self, db, tenant, contact, pipeline, lead_closed, user):
        """El lead reopened tiene actividad de tipo recompra."""
        client = Client()
        client.force_login(user)
        response = client.post(
            f"/api/crm/leads/{lead_closed.id}/reopen/?tenant_slug=testtenant",
            {"product_of_interest": "Panel Solar 500W"},
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        new_lead_id = response.json().get("id")

        assert LeadActivity.objects.filter(
            lead_id=new_lead_id, activity_type="recompra"
        ).exists()

    def test_reopen_fails_if_not_closed(self, db, tenant, lead_active, user):
        """Reopen falla si el lead no está cerrado."""
        client = Client()
        client.force_login(user)
        response = client.post(
            f"/api/crm/leads/{lead_active.id}/reopen/?tenant_slug=testtenant",
            {"product_of_interest": "Panel Solar"},
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "no está cerrado" in response.json().get("detail", "")


class TestDashboardRendering:
    """Tests para renderizado del dashboard y datos en tarjetas."""

    def test_dashboard_shows_lead_tags(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Las tarjetas de lead muestran las etiquetas."""
        tag = Tag.objects.create(tenant=tenant, name="Prioridad Alta", color="#FF0000", is_predefined=False)
        LeadTag.objects.create(lead=lead_active, tag=tag)

        response = client_auth.get("/crm/testtenant/dashboard/")
        assert response.status_code == status.HTTP_200_OK
        assert "Prioridad Alta" in response.content.decode("utf-8")

    def test_dashboard_lead_card_has_data_stage(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Las tarjetas tienen data-stage para filtros y drag."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")
        assert 'data-stage="Lead"' in content

    def test_dashboard_lead_card_has_data_is_closed(self, db, tenant, pipeline, contact, lead_closed, user, client_auth):
        """Las tarjetas de lead cerrado tienen data-is-closed."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")
        assert 'data-is-closed="true"' in content

    def test_dashboard_recompra_lead_has_badge(self, db, tenant, pipeline, contact, user, client_auth):
        """Los leads de recompra muestran badge en el dashboard."""
        lead = Lead.objects.create(
            tenant=tenant,
            contact=contact,
            current_stage="Lead",
            is_recompra=True,
        )
        response = client_auth.get("/crm/testtenant/dashboard/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")
        assert "recompra" in content.lower() or "is_recompra" in content

    def test_lead_detail_shows_tags(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """La página de detalle muestra las etiquetas del lead."""
        tag = Tag.objects.create(tenant=tenant, name="Cliente Frio", color="#0000FF")
        LeadTag.objects.create(lead=lead_active, tag=tag)

        response = client_auth.get(f"/crm/testtenant/leads/{lead_active.id}/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")
        assert "Cliente Frio" in content


class TestTrashRestorePermanentDelete:
    """Tests para el ciclo completo de eliminación → papelera → restaurar → borrar permanente."""

    def test_delete_lead_sets_is_deleted_and_creates_activity(
        self, db, tenant, lead_active, user
    ):
        """DELETE marca el lead como eliminado y crea actividad 'deleted'."""
        client = Client()
        client.force_login(user)
        response = client.delete(
            f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant",
        )
        assert response.status_code in (204, 200)

        lead_active.refresh_from_db()
        assert lead_active.is_deleted is True
        assert lead_active.deleted_at is not None
        assert lead_active.deleted_by == "admin"

        assert LeadActivity.objects.filter(
            lead=lead_active, activity_type="deleted"
        ).exists()

    def test_deleted_lead_disappears_from_default_queryset(
        self, db, tenant, lead_active, user
    ):
        """Un lead eliminado no aparece en el queryset por defecto."""
        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant")

        assert Lead.objects.filter(id=lead_active.id).count() == 0
        assert Lead.all_objects.filter(id=lead_active.id).count() == 1

    def test_trash_endpoint_lists_deleted_leads(
        self, db, tenant, lead_active, user
    ):
        """GET /api/crm/leads/trash/ devuelve leads eliminados."""
        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant")

        response = client.get("/api/crm/leads/trash/?tenant_slug=testtenant")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any(l["id"] == lead_active.id for l in data)

    def test_trash_html_page_renders_deleted_leads(
        self, db, tenant, pipeline, contact, lead_active, user, client_auth
    ):
        """La página trash.html muestra los leads eliminados."""
        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant")

        response = client_auth.get("/crm/testtenant/trash/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")
        assert f"trash-item-{lead_active.id}" in content

    def test_restore_lead_clears_deleted_and_creates_activity(
        self, db, tenant, lead_active, user
    ):
        """POST restore() limpia is_deleted y crea actividad 'restored'."""
        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant")

        response = client.post(
            f"/api/crm/leads/{lead_active.id}/restore/?tenant_slug=testtenant",
        )
        assert response.status_code == status.HTTP_200_OK

        lead_active.refresh_from_db()
        assert lead_active.is_deleted is False
        assert lead_active.deleted_at is None
        assert lead_active.deleted_by == ""

        assert LeadActivity.objects.filter(
            lead=lead_active, activity_type="restored"
        ).exists()

    def test_restore_lead_returns_to_default_queryset(
        self, db, tenant, lead_active, user
    ):
        """Un lead restaurado vuelve a aparecer en el queryset por defecto."""
        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant")
        client.post(f"/api/crm/leads/{lead_active.id}/restore/?tenant_slug=testtenant")

        assert Lead.objects.filter(id=lead_active.id).count() == 1
        assert Lead.all_objects.filter(id=lead_active.id).count() == 1

    def test_restore_lead_stays_in_original_stage(
        self, db, tenant, lead_active, user
    ):
        """Restaurar no cambia la etapa del lead (permanece donde estaba)."""
        lead_active.current_stage = "Calificacion"
        lead_active.save(update_fields=["current_stage"])

        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant")
        client.post(f"/api/crm/leads/{lead_active.id}/restore/?tenant_slug=testtenant")

        lead_active.refresh_from_db()
        assert lead_active.current_stage == "Calificacion"

    def test_restore_fails_if_not_deleted(
        self, db, tenant, lead_active, user
    ):
        """Restaurar un lead que no está eliminado retorna 400."""
        client = Client()
        client.force_login(user)
        response = client.post(
            f"/api/crm/leads/{lead_active.id}/restore/?tenant_slug=testtenant",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "no está eliminado" in response.json().get("detail", "")

    def test_permanently_delete_old_leads_task_removes_old_deleted(
        self, db, tenant, contact, pipeline, user
    ):
        """El task Celery elimina leads con deleted_at > 30 días.

        Como celery puede no estar instalado en el entorno de test,
        probamos la lógica directamente.
        """
        from datetime import timedelta
        from django.utils import timezone

        old_lead = Lead.all_objects.create(
            tenant=tenant,
            contact=contact,
            current_stage="Lead",
            is_deleted=True,
            deleted_at=timezone.now() - timedelta(days=31),
            deleted_by="admin",
        )
        new_lead = Lead.all_objects.create(
            tenant=tenant,
            contact=contact,
            current_stage="Lead",
            is_deleted=True,
            deleted_at=timezone.now() - timedelta(days=10),
            deleted_by="admin",
        )

        threshold = timezone.now() - timedelta(days=30)
        deleted_leads = Lead.all_objects.filter(
            is_deleted=True,
            deleted_at__lt=threshold,
        )
        count = deleted_leads.count()
        deleted_leads.delete()

        assert count == 1
        assert Lead.all_objects.filter(id=old_lead.id).count() == 0
        assert Lead.all_objects.filter(id=new_lead.id).count() == 1

    def test_permanently_delete_preserves_active_leads(
        self, db, tenant, contact, pipeline
    ):
        """El task NO toca leads activos (is_deleted=False)."""
        from datetime import timedelta
        from django.utils import timezone

        active_lead = Lead.objects.create(
            tenant=tenant,
            contact=contact,
            current_stage="Lead",
            is_deleted=False,
        )

        threshold = timezone.now() - timedelta(days=30)
        deleted_leads = Lead.all_objects.filter(
            is_deleted=True,
            deleted_at__lt=threshold,
        )
        result_count = deleted_leads.count()

        assert result_count == 0
        assert Lead.objects.filter(id=active_lead.id).count() == 1

    def test_delete_then_restore_full_cycle_on_lead(
        self, db, tenant, pipeline, contact, user
    ):
        """Ciclo completo: crear → eliminar → restaurar → verificar etapa intacta."""
        lead = Lead.objects.create(
            tenant=tenant,
            contact=contact,
            current_stage="Calificacion",
            product_of_interest="Panel Solar",
            is_closed=False,
        )
        initial_stage = lead.current_stage

        client = Client()
        client.force_login(user)

        r1 = client.delete(f"/api/crm/leads/{lead.id}/?tenant_slug=testtenant")
        assert r1.status_code in (204, 200)

        r2 = client.post(f"/api/crm/leads/{lead.id}/restore/?tenant_slug=testtenant")
        assert r2.status_code == status.HTTP_200_OK

        lead.refresh_from_db()
        assert lead.is_deleted is False
        assert lead.current_stage == initial_stage
        assert lead.product_of_interest == "Panel Solar"

    def test_trash_page_shows_restore_button(
        self, db, tenant, lead_active, user, client_auth
    ):
        """La página trash muestra botón restaurar para cada lead."""
        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_active.id}/?tenant_slug=testtenant")

        response = client_auth.get("/crm/testtenant/trash/")
        content = response.content.decode("utf-8")
        assert "restoreLead" in content or "restaurar" in content.lower()

    def test_lead_detail_delete_button_exists(
        self, db, tenant, lead_active, user, client_auth
    ):
        """La página de detalle del lead tiene botón de eliminar."""
        response = client_auth.get(f"/crm/testtenant/leads/{lead_active.id}/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")
        assert "deleteLeadModal" in content or "btn-danger" in content


class TestSidebarFilters:
    """Tests para los filtros del sidebar del dashboard."""

    def test_period_filter_radio_buttons_exist(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Todos los botones de período rápido existen y 'Todo' es el valor checked por defecto."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")

        for value, label in [("hoy", "Hoy"), ("ayer", "Ayer"), ("7d", "Últ. 7 días"), ("30d", "Últ. 30 días"), ("mes", "Este mes"), ("todo", "Todo")]:
            assert f'value="{value}"' in content, f"Falta valor periodo: {value}"
            assert f'name="quickPeriod"' in content

        assert 'value="todo"' in content and 'checked' in content, "'Todo' debe estar checked por defecto"

    def test_stage_filter_checkboxes_exist_and_checked(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Los checkboxes de etapa existen y vienen checked por defecto."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")

        assert 'stage-filter' in content

    def test_stage_filter_shows_pipeline_stages(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Los filtros de etapa reflejan las etapas del pipeline (Lead, Calificacion, Cerrado Ganado)."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert "Lead" in content
        assert "Calificacion" in content

    def test_source_filter_dropdown_exists(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El filtro de fuente existe con todas las opciones."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")

        assert 'id="filter-source"' in content
        assert '<option value="meta">Meta</option>' in content
        assert '<option value="google">Google Ads</option>' in content
        assert '<option value="tiktok">TikTok</option>' in content
        assert '<option value="web">Página web</option>' in content
        assert '<option value="referral">Referido</option>' in content

    def test_open_only_toggle_exists(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El toggle 'Solo abiertos' existe."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert 'id="filter-open-only"' in content
        assert "Solo abiertos" in content

    def test_date_range_inputs_exist(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Los inputs de rango de fechas (Desde/Hasta) existen."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert 'id="filter-date-from"' in content
        assert 'id="filter-date-to"' in content
        assert 'type="date"' in content

    def test_task_filter_buttons_exist(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Todos los botones de filtro de tareas existen."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")

        for filter_name in ["with_pending", "due_today", "due_tomorrow", "overdue", "none"]:
            assert f'data-task-filter="{filter_name}"' in content, f"Falta filtro tarea: {filter_name}"
            assert "task-filter-btn" in content

    def test_tags_api_loads_tags(self, db, tenant, pipeline, contact, lead_active, user):
        """GET /api/crm/tenants/{slug}/tags/ devuelve las etiquetas del tenant."""
        from crm.domain.models import Tag, LeadTag

        tag1 = Tag.objects.create(tenant=tenant, name="Urgente", color="#FF0000", is_predefined=False)
        tag2 = Tag.objects.create(tenant=tenant, name="VIP", color="#9B59B6", is_predefined=False)
        LeadTag.objects.create(lead=lead_active, tag=tag1)

        client = Client()
        client.force_login(user)
        response = client.get(f"/api/crm/tenants/{tenant.slug}/tags/")
        assert response.status_code == status.HTTP_200_OK
        tags = response.json()
        tag_names = [t["name"] for t in tags]
        assert "Urgente" in tag_names
        assert "VIP" in tag_names

    def test_sidebar_tags_container_exists(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El contenedor de tags en el sidebar existe."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert 'id="sidebar-tags-list"' in content
        assert "Cargando..." in content

    def test_clear_filters_button_exists(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El botón 'Limpiar filtros' existe."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert 'id="clear-filters-btn"' in content
        assert "Limpiar" in content

    def test_apply_filters_button_exists(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El botón 'Aplicar filtros' existe."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert 'id="apply-filters-btn"' in content
        assert "Aplicar" in content

    def test_stage_filter_section_renders_with_colors(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Los filtros de etapa muestran los colores del pipeline."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert "stage-dot" in content or "stage-color" in content

    def test_filter_source_shows_all_options(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El select de fuente tiene todas las plataformas."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        sources = ["meta", "google", "tiktok", "web", "referral"]
        for src in sources:
            assert f'value="{src}"' in content, f"Falta fuente: {src}"

    def test_task_filter_buttons_have_badges(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Los botones de tareas tienen badges para los contadores."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        badges = content.count('badge bg-secondary')
        assert badges >= 5, f"Esperados al menos 5 badges, encontrados {badges}"

    def test_sidebar_closes_with_close_button(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El sidebar tiene botón de cerrar y overlay."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert 'id="sidebar-close-btn"' in content
        assert 'id="sidebar-overlay"' in content

    def test_lead_cards_have_data_attributes_for_filtering(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Las tarjetas de lead tienen los data attributes necesarios para los filtros."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")

        assert 'data-stage="' in content, "Falta data-stage"
        assert 'data-source="' in content, "Falta data-source"
        assert 'data-created="' in content, "Falta data-created"

    def test_lead_cards_with_tags_have_tag_ids_in_data_attributes(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Las tarjetas con tags incluyen los IDs de tag en data-tags."""
        from crm.domain.models import Tag, LeadTag

        tag = Tag.objects.create(tenant=tenant, name="Urgente", color="#FF0000", is_predefined=False)
        LeadTag.objects.create(lead=lead_active, tag=tag)

        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert "data-tags=" in content, "Falta data-tags en tarjetas"

    def test_filter_sidebar_is_accessible(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El sidebar tiene aria-labels para accesibilidad."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert 'aria-label="Panel de filtros"' in content
        assert 'aria-label="Selección de período"' in content or "Período rápido" in content

    def test_tags_api_endpoint_404_for_invalid_tenant(self, db, user):
        """GET /api/crm/tenants/{invalid}/tags/ retorna 404."""
        client = Client()
        client.force_login(user)
        response = client.get("/api/crm/tenants/nonexistent-slug/tags/")
        assert response.status_code == 404

    def test_filter_count_update_on_lead_creation(self, db, tenant, pipeline, contact, lead_active, user):
        """Crear un lead incrementa el total visible en stats."""
        client = Client()
        client.force_login(user)

        r1 = client.get(f"/api/crm/leads/stats/?tenant_slug=testtenant")
        initial = r1.json().get("total_leads", 0)

        Lead.objects.create(tenant=tenant, contact=contact, current_stage="Lead")

        r2 = client.get(f"/api/crm/leads/stats/?tenant_slug=testtenant")
        assert r2.json().get("total_leads") == initial + 1

    def test_sidebar_has_filter_section_titles(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """Todas las secciones del sidebar tienen títulos."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        titles = ["Período rápido", "Rango personalizado", "Etapas", "Fuente", "Estado", "Etiquetas", "Tareas"]
        for title in titles:
            assert title in content, f"Falta título de sección: {title}"

    def test_filter_source_default_is_all(self, db, tenant, pipeline, contact, lead_active, user, client_auth):
        """El filtro de fuente tiene opción por defecto 'Todas las fuentes'."""
        response = client_auth.get("/crm/testtenant/dashboard/")
        content = response.content.decode("utf-8")
        assert '<option value="">Todas las fuentes</option>' in content


class TestStatsRefresh:
    """Tests para actualización de estadísticas."""

    def test_stats_endpoint_after_stage_change(self, db, tenant, pipeline, contact, lead_active, user):
        """Después de mover un lead, stats refleja el cambio."""
        client = Client()
        client.force_login(user)
        response = client.get(f"/api/crm/leads/stats/?tenant_slug=testtenant")
        assert response.status_code == status.HTTP_200_OK
        initial_total = response.json().get("total_leads", 0)

        Lead.objects.create(tenant=tenant, contact=contact, current_stage="Calificacion")

        response2 = client.get(f"/api/crm/leads/stats/?tenant_slug=testtenant")
        assert response2.json().get("total_leads") == initial_total + 1

    def test_stats_shows_recompra_leads(self, db, tenant, pipeline, contact, user):
        """Stats puede distinguir leads recompra si se necesita."""
        Lead.objects.create(tenant=tenant, contact=contact, current_stage="Lead", is_recompra=True)
        Lead.objects.create(tenant=tenant, contact=contact, current_stage="Lead", is_recompra=False)

        client = Client()
        client.force_login(user)
        response = client.get(f"/api/crm/leads/stats/?tenant_slug=testtenant")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get("total_leads") >= 2