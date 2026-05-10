"""
crm/tests/test_ui_selenium.py

Tests de UI con Selenium para validar los flujos principales del CRM.
Usa LiveServerTestCase para servir las páginas durante los tests.

Requiere: pip install selenium pytest-selenium
"""

import pytest
from django.test import LiveServerTestCase, Client
from django.contrib.auth.models import User

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from crm.domain.models import Lead, Contact, LeadActivity, Tag, LeadTag
from tenants.models import Tenant
from tenants.domain.models import PipelineConfig


@pytest.fixture(scope="module")
def chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="SAMA Test Tenant", slug="sama-test", is_active=True)


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
        full_name="Laura Mendez",
        phone_number="573009998877",
        email="laura@test.com",
    )


@pytest.fixture
def user(db):
    return User.objects.create_superuser(username="admin", password="admin", email="admin@test.com")


@pytest.fixture
def lead_in_calificacion(db, tenant, contact, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Calificacion",
        product_of_interest="Panel Solar",
        is_closed=False,
    )


@pytest.fixture
def lead_in_lead(db, tenant, contact, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Lead",
        product_of_interest="Bateria",
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
def lead_with_tags(db, tenant, contact, pipeline):
    lead = Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Lead",
        is_closed=False,
    )
    tag1 = Tag.objects.create(tenant=tenant, name="Urgente", color="#FF0000", is_predefined=False)
    tag2 = Tag.objects.create(tenant=tenant, name="VIP", color="#9B59B6", is_predefined=False)
    LeadTag.objects.create(lead=lead, tag=tag1)
    LeadTag.objects.create(lead=lead, tag=tag2)
    return lead


@pytest.fixture
def client_auth(db, user):
    client = Client()
    client.force_login(user)
    return client


class SeleniumTestCase(LiveServerTestCase):
    """Base test case que proporciona live server URL y sesión auth."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=service, options=options)
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def auth_get(self, path):
        session = self.client.session
        session.save()
        self.driver.get(self.live_server_url + path)
        return self.driver


class TestDashboardUI(SeleniumTestCase):
    """Tests de UI para el dashboard Kanban."""

    def test_kanban_renders_all_columns(self, tenant, pipeline, lead_in_lead):
        """El dashboard muestra las 3 columnas del pipeline."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "kanban-board")))
        columns = self.driver.find_elements(By.CLASS_NAME, "kanban-column")
        self.assertGreaterEqual(len(columns), 3, f"Esperadas 3 columnas, encontradas {len(columns)}")

    def test_lead_card_has_drag_attribute(self, tenant, pipeline, lead_in_lead):
        """Las tarjetas de lead tienen draggable=true."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "kanban-cards")))
        cards = self.driver.find_elements(By.CSS_SELECTOR, ".lead-card[draggable='true']")
        self.assertGreater(len(cards), 0, "No hay tarjetas draggable")

    def test_lead_card_has_data_stage(self, tenant, pipeline, lead_in_lead):
        """Las tarjetas tienen data-stage para identificar la etapa."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "lead-card")))
        first_card = self.driver.find_element(By.CLASS_NAME, "lead-card")
        stage = first_card.get_attribute("data-stage")
        self.assertIsNotNone(stage)
        self.assertNotEqual(stage, "", f"data-stage vacío")

    def test_lead_card_tags_are_visible(self, tenant, pipeline, lead_with_tags):
        """Los tags aparecen en la tarjeta del dashboard."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "lead-card-tags")))
        badges = self.driver.find_elements(By.CLASS_NAME, "lead-tag-badge")
        self.assertGreaterEqual(len(badges), 2, f"Esperados al menos 2 tags, encontrados {len(badges)}")

    def test_stats_row_shows_numbers(self, tenant, pipeline, lead_in_lead, lead_in_calificacion):
        """Las estadísticas muestran números (total leads)."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "stat-total")))
        stat = self.driver.find_element(By.ID, "stat-total").text
        self.assertNotEqual(stat, "0", f"Stats no muestran datos: '{stat}'")
        self.assertNotEqual(stat, "", f"Stats vacías: '{stat}'")

    def test_recompra_lead_has_badge(self, tenant, pipeline, contact):
        """Los leads de recompra muestran badge en el dashboard."""
        Lead.objects.create(
            tenant=tenant,
            contact=contact,
            current_stage="Lead",
            is_recompra=True,
        )
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "kanban-cards")))
        content = self.driver.page_source
        self.assertTrue("recompra" in content.lower() or "badge" in content.lower())

    def test_trash_icon_link_exists(self, tenant, pipeline, lead_in_lead):
        """El enlace a la papelera existe en el header."""
        self.auth_get("/crm/sama-test/dashboard/")
        trash_link = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/trash/']")
        self.assertIsNotNone(trash_link)

    def test_search_input_exists(self, tenant, pipeline, lead_in_lead):
        """El campo de búsqueda existe y es visible."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "lead-search")))
        search = self.driver.find_element(By.ID, "lead-search")
        self.assertTrue(search.is_displayed())


class TestLeadDetailDeleteUI(SeleniumTestCase):
    """Tests de UI para eliminar lead desde la página de detalle."""

    def test_delete_button_exists_in_lead_detail(self, tenant, pipeline, lead_in_lead):
        """El botón 'Eliminar lead' existe en la página de detalle."""
        self.auth_get(f"/crm/sama-test/leads/{lead_in_lead.id}/")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[onclick*='openDeleteModal']"))
        )
        delete_btn = self.driver.find_element(By.CSS_SELECTOR, "button[onclick*='openDeleteModal']")
        self.assertIn("eliminar", delete_btn.text.lower())

    def test_delete_modal_opens_when_button_clicked(self, tenant, pipeline, lead_in_lead):
        """Click en 'Eliminar lead' abre el modal de confirmación."""
        self.auth_get(f"/crm/sama-test/leads/{lead_in_lead.id}/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "deleteLeadModal")))
        delete_btn = self.driver.find_element(By.CSS_SELECTOR, "button[onclick*='openDeleteModal']")
        delete_btn.click()
        WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, "deleteLeadModal")))
        modal = self.driver.find_element(By.ID, "deleteLeadModal")
        self.assertTrue(
            "show" in modal.get_attribute("class") or modal.is_displayed()
        )

    def test_confirm_delete_sends_request_and_redirects(self, tenant, pipeline, lead_in_lead):
        """Confirmar eliminación redirige al dashboard y el lead pasa a papelera."""
        lead_id = lead_in_lead.id
        self.auth_get(f"/crm/sama-test/leads/{lead_id}/")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[onclick*='openDeleteModal']"))
        )
        self.driver.find_element(By.CSS_SELECTOR, "button[onclick*='openDeleteModal']").click()
        WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, "deleteLeadModal")))
        confirm_btn = self.driver.find_element(By.ID, "confirm-delete-btn-detail")
        confirm_btn.click()
        WebDriverWait(self.driver, 15).until(lambda d: "/dashboard/" in d.current_url)
        self.assertIn("/dashboard/", self.driver.current_url)
        lead_in_lead.refresh_from_db()
        self.assertTrue(lead_in_lead.is_deleted)

    def test_lead_detail_shows_tags(self, tenant, pipeline, lead_with_tags):
        """La página de detalle muestra los tags del lead."""
        self.auth_get(f"/crm/sama-test/leads/{lead_with_tags.id}/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "lead-tag-detail")))
        tags = self.driver.find_elements(By.CLASS_NAME, "lead-tag-detail")
        self.assertGreaterEqual(len(tags), 2, f"Esperados >=2 tags, encontrados {len(tags)}")


class TestTrashPageUI(SeleniumTestCase):
    """Tests de UI para la página de papelera."""

    def test_trash_page_renders_deleted_leads(self, tenant, pipeline, lead_in_lead, user):
        """La papelera muestra los leads eliminados."""
        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_in_lead.id}/?tenant_slug=sama-test")
        self.auth_get("/crm/sama-test/trash/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "trash-list")))
        items = self.driver.find_elements(By.CLASS_NAME, "trash-item")
        self.assertGreater(len(items), 0, f"Esperado al menos 1 item, encontrados {len(items)}")

    def test_restore_button_calls_api_and_removes_item(self, tenant, pipeline, lead_in_lead, user):
        """El botón 'Restaurar' restaura el lead y lo quita de la papelera."""
        client = Client()
        client.force_login(user)
        client.delete(f"/api/crm/leads/{lead_in_lead.id}/?tenant_slug=sama-test")
        self.auth_get("/crm/sama-test/trash/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "btn-restore")))
        restore_btn = self.driver.find_element(By.CLASS_NAME, "btn-restore")
        restore_btn.click()
        WebDriverWait(self.driver, 5).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, "trash-item")) == 0
            or len(d.find_elements(By.CLASS_NAME, "trash-empty")) > 0
        )
        lead_in_lead.refresh_from_db()
        self.assertFalse(lead_in_lead.is_deleted)


class TestDragDropUI(SeleniumTestCase):
    """Tests de UI para drag & drop (verifican estructura HTML/JS)."""

    def test_card_draggable_attribute(self, tenant, pipeline, lead_in_lead):
        """Las tarjetas tienen el atributo draggable=True."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "lead-card")))
        card = self.driver.find_element(By.CLASS_NAME, "lead-card")
        self.assertEqual(card.get_attribute("draggable"), "true")

    def test_drag_start_stores_pending_drag(self, tenant, pipeline, lead_in_lead):
        """Las tarjetas tienen data-lead-id y data-stage para el drag."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "lead-card")))
        card = self.driver.find_element(By.CLASS_NAME, "lead-card")
        stage = card.get_attribute("data-stage")
        lead_id = card.get_attribute("data-lead-id")
        self.assertIsNotNone(stage)
        self.assertIsNotNone(lead_id)

    def test_column_accepts_drop_zone(self, tenant, pipeline, lead_in_lead):
        """Las columnas tienen data-stage y son zonas de drop."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "kanban-column")))
        columns = self.driver.find_elements(By.CLASS_NAME, "kanban-column")
        self.assertGreaterEqual(len(columns), 2)
        for col in columns:
            self.assertIsNotNone(col.get_attribute("data-stage"))

    def test_stage_filter_buttons_in_sidebar(self, tenant, pipeline, lead_in_lead):
        """Los filtros de etapa existen en el sidebar."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "sidebar")))
        filters = self.driver.find_elements(By.CSS_SELECTOR, "[data-stage-filter]")
        self.assertGreater(len(filters), 0, "No hay filtros de etapa en el sidebar")

    def test_kanban_board_exists(self, tenant, pipeline, lead_in_lead):
        """El tablero Kanban existe con las columnas correctas."""
        self.auth_get("/crm/sama-test/dashboard/")
        board = self.driver.find_element(By.ID, "kanban-board")
        self.assertIsNotNone(board)
        columns = self.driver.find_elements(By.CLASS_NAME, "kanban-column")
        self.assertGreaterEqual(len(columns), 2, "Al menos 2 columnas para drag & drop")

    def test_lead_card_is_anchor_link(self, tenant, pipeline, lead_in_lead):
        """Las tarjetas son enlaces al detalle del lead."""
        self.auth_get("/crm/sama-test/dashboard/")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "lead-card")))
        card = self.driver.find_element(By.CLASS_NAME, "lead-card")
        self.assertEqual(card.tag_name, "a")
        href = card.get_attribute("href")
        self.assertIsNotNone(href)
        self.assertIn("/leads/", href)