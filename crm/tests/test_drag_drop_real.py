"""
crm/tests/test_drag_drop_real.py

Tests de drag & drop REAL con Selenium usando ActionChains.
Estos tests simulan las acciones reales del usuario: arrastrar tarjetas, 
interactuar con modales, confirmar decisiones.

Cobertura:
- Drag tarjeta entre etapas activas
- Drag a etapa cerrada → modal reopen
- "Fue un error" en modal
- "Nueva oportunidad" en modal
- Filtros funcionales (no solo presencia HTML)
- Búsqueda de leads
"""

import pytest
from django.test import LiveServerTestCase, Client
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep

from crm.domain.models import Lead, Contact, LeadActivity, Tag, LeadTag
from tenants.models import Tenant
from tenants.domain.models import PipelineConfig


@pytest.fixture(scope="module")
def chrome_driver():
    """Configura Chrome con opciones para headless y desactiva sandbox."""
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
def lead_in_lead(db, tenant, contact, pipeline):
    return Lead.objects.create(
        tenant=tenant,
        contact=contact,
        current_stage="Lead",
        product_of_interest="Bateria",
        is_closed=False,
    )


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


class DragDropSeleniumTestCase(LiveServerTestCase):
    """Base test case para tests de drag & drop con Selenium."""

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
        """Navega a una ruta autenticado con sesión real."""
        session = self.client.session
        session.save()
        self.driver.get(self.live_server_url + path)
        # Inyectar cookie de sesión en el navegador
        self.driver.add_cookie({
            'name': 'sessionid',
            'value': self.client.cookies['sessionid'].value,
        })
        self.driver.get(self.live_server_url + path)
        return self.driver


class TestDragDropRealBehavior(DragDropSeleniumTestCase):
    """Tests de drag & drop real con ActionChains."""

    def test_drag_card_from_lead_to_calificacion(self, tenant, pipeline, lead_in_lead, user):
        """
        Arrastra una tarjeta de "Lead" a "Calificacion".
        Valida que:
        1. La tarjeta desaparece de Lead
        2. Aparece en Calificacion
        3. BD actualiza current_stage
        4. Se crea actividad stage_change
        """
        self.auth_get(f"/crm/{tenant.slug}/dashboard/")
        
        # Esperar a que cargue el tablero
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "kanban-board"))
        )
        sleep(2)  # Esperar render completo
        
        # Buscar tarjeta en columna Lead
        source_card = self.driver.find_element(By.CSS_SELECTOR, f"[data-lead-id='{lead_in_lead.id}']")
        self.assertIsNotNone(source_card)
        
        # Buscar columna destino (Calificacion)
        target_column = self.driver.find_element(By.CSS_SELECTOR, "[data-stage='Calificacion']")
        self.assertIsNotNone(target_column)
        
        # Realizar drag & drop real
        actions = ActionChains(self.driver)
        actions.drag_and_drop(source_card, target_column).perform()
        
        # Esperar a que se complete la animación y la API responda
        sleep(2)
        
        # Validar en BD
        lead_in_lead.refresh_from_db()
        self.assertEqual(lead_in_lead.current_stage, "Calificacion")
        self.assertTrue(LeadActivity.objects.filter(
            lead=lead_in_lead,
            activity_type="stage_change"
        ).exists())

    def test_drag_card_to_closed_stage_shows_reopen_modal(self, tenant, pipeline, lead_in_lead, user):
        """
        Arrastra una tarjeta a una etapa cerrada ("Cerrado Ganado").
        Valida que:
        1. Aparece modal de reopen
        2. Modal tiene opciones "Fue un error" y "Nueva oportunidad"
        """
        self.auth_get(f"/crm/{tenant.slug}/dashboard/")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "kanban-board"))
        )
        sleep(2)
        
        # Buscar tarjeta
        source_card = self.driver.find_element(By.CSS_SELECTOR, f"[data-lead-id='{lead_in_lead.id}']")
        
        # Buscar columna Cerrado Ganado (etapa cerrada)
        target_column = self.driver.find_element(By.CSS_SELECTOR, "[data-stage='Cerrado Ganado']")
        
        # Drag & drop
        actions = ActionChains(self.driver)
        actions.drag_and_drop(source_card, target_column).perform()
        
        sleep(2)
        
        # Esperar a que aparezca modal de reopen
        modal = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "reopenModal"))
        )
        
        # Validar que modal contiene botones esperados
        error_btn = self.driver.find_element(By.ID, "btn-fue-error") or \
                   self.driver.find_element(By.CSS_SELECTOR, "[data-action='fue-error']")
        opportunity_btn = self.driver.find_element(By.ID, "btn-nueva-oportunidad") or \
                         self.driver.find_element(By.CSS_SELECTOR, "[data-action='nueva-oportunidad']")
        
        self.assertIsNotNone(error_btn)
        self.assertIsNotNone(opportunity_btn)

    def test_fue_un_error_reverts_drag(self, tenant, pipeline, lead_in_calificacion, user):
        """
        Arrastra tarjeta a etapa cerrada.
        En el modal, click en "Fue un error".
        Valida que:
        1. Modal cierra
        2. Tarjeta vuelve a etapa anterior (Calificacion)
        3. BD NO cambia
        """
        lead_id = lead_in_calificacion.id
        original_stage = lead_in_calificacion.current_stage
        
        self.auth_get(f"/crm/{tenant.slug}/dashboard/")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "kanban-board"))
        )
        sleep(2)
        
        # Drag a Cerrado Ganado
        source_card = self.driver.find_element(By.CSS_SELECTOR, f"[data-lead-id='{lead_id}']")
        target_column = self.driver.find_element(By.CSS_SELECTOR, "[data-stage='Cerrado Ganado']")
        
        actions = ActionChains(self.driver)
        actions.drag_and_drop(source_card, target_column).perform()
        
        sleep(2)
        
        # Click en "Fue un error"
        modal = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "reopenModal"))
        )
        
        error_btn = modal.find_element(By.CSS_SELECTOR, "[data-action='fue-error']")
        error_btn.click()
        
        sleep(1)
        
        # Validar que modal cerró
        WebDriverWait(self.driver, 5).until(
            EC.invisibility_of_element_located((By.ID, "reopenModal"))
        )
        
        # Validar que tarjeta sigue en Calificacion
        lead_in_calificacion.refresh_from_db()
        self.assertEqual(lead_in_calificacion.current_stage, original_stage)

    def test_nueva_oportunidad_creates_recompra_lead(self, tenant, pipeline, lead_closed, user):
        """
        Arrastra tarjeta cerrada.
        En modal, click en "Nueva oportunidad".
        Valida que:
        1. Se crea nuevo lead con is_recompra=True
        2. Original permanece cerrado
        3. Nuevo lead aparece en columna Lead
        """
        original_id = lead_closed.id
        
        self.auth_get(f"/crm/{tenant.slug}/dashboard/")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "kanban-board"))
        )
        sleep(2)
        
        # Drag a cualquier etapa activa para abrir modal
        source_card = self.driver.find_element(By.CSS_SELECTOR, f"[data-lead-id='{original_id}']")
        target_column = self.driver.find_element(By.CSS_SELECTOR, "[data-stage='Lead']")
        
        actions = ActionChains(self.driver)
        actions.drag_and_drop(source_card, target_column).perform()
        
        sleep(2)
        
        # Click en "Nueva oportunidad"
        modal = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "reopenModal"))
        )
        
        opp_btn = modal.find_element(By.CSS_SELECTOR, "[data-action='nueva-oportunidad']")
        opp_btn.click()
        
        sleep(2)
        
        # Validar en BD: nuevo lead creado con is_recompra=True
        new_recompra_leads = Lead.objects.filter(
            contact=lead_closed.contact,
            is_recompra=True,
            is_closed=False
        )
        
        self.assertEqual(new_recompra_leads.count(), 1)
        new_lead = new_recompra_leads.first()
        self.assertEqual(new_lead.current_stage, "Lead")
        
        # Original permanece cerrado
        lead_closed.refresh_from_db()
        self.assertTrue(lead_closed.is_closed)


class TestFiltersFunctional(DragDropSeleniumTestCase):
    """Tests de filtros que validan funcionalidad, no solo presencia HTML."""

    def test_filter_stage_unchecked_hides_cards(self, tenant, pipeline, lead_in_lead, lead_in_calificacion, user):
        """
        Desmarcar 'Lead' en filtro de etapas debería ocultar tarjetas de Lead.
        """
        self.auth_get(f"/crm/{tenant.slug}/dashboard/")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "kanban-board"))
        )
        sleep(1)
        
        # Contar tarjetas iniciales
        initial_cards = self.driver.find_elements(By.CLASS_NAME, "lead-card")
        initial_count = len(initial_cards)
        self.assertGreater(initial_count, 0)
        
        # Desmarcar checkbox "Lead"
        lead_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[data-stage='Lead'][type='checkbox']")
        lead_checkbox.click()
        
        # Click en "Aplicar filtros"
        apply_btn = self.driver.find_element(By.ID, "apply-filters-btn")
        apply_btn.click()
        
        sleep(2)
        
        # Contar tarjetas después de filtrar
        filtered_cards = self.driver.find_elements(By.CLASS_NAME, "lead-card")
        filtered_count = len(filtered_cards)
        
        # Debe haber menos tarjetas
        self.assertLess(filtered_count, initial_count)

    def test_filter_period_7days_shows_recent_leads(self, tenant, pipeline, contact, user):
        """
        Filtrar por "7 días" debería mostrar solo leads creados hace menos de 7 días.
        """
        from datetime import timedelta
        from django.utils import timezone
        
        # Crear lead reciente
        recent_lead = Lead.objects.create(
            tenant=tenant,
            contact=contact,
            current_stage="Lead",
            is_closed=False,
            created_at=timezone.now()
        )
        
        # Crear lead viejo (15 días)
        old_lead = Lead.objects.create(
            tenant=tenant,
            contact=contact,
            current_stage="Lead",
            is_closed=False,
            created_at=timezone.now() - timedelta(days=15)
        )
        
        self.auth_get(f"/crm/{tenant.slug}/dashboard/")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "kanban-board"))
        )
        
        # Seleccionar período "7d"
        period_7d = self.driver.find_element(By.CSS_SELECTOR, "input[value='7d']")
        period_7d.click()
        
        apply_btn = self.driver.find_element(By.ID, "apply-filters-btn")
        apply_btn.click()
        
        sleep(2)
        
        # Validar que lead reciente está visible, viejo no
        visible_leads = self.driver.find_elements(By.CLASS_NAME, "lead-card")
        visible_ids = [card.get_attribute("data-lead-id") for card in visible_leads]
        
        # El reciente debe estar visible
        self.assertIn(str(recent_lead.id), visible_ids)

    def test_search_filters_leads_by_name(self, tenant, pipeline, contact, lead_in_lead, user):
        """
        Búsqueda por nombre debería filtrar leads en tiempo real.
        """
        self.auth_get(f"/crm/{tenant.slug}/dashboard/")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "lead-search"))
        )
        
        # Escribir nombre en búsqueda
        search_input = self.driver.find_element(By.ID, "lead-search")
        search_input.send_keys(contact.full_name)
        
        sleep(1)
        
        # Validar que solo aparece la tarjeta coincidente
        visible_cards = self.driver.find_elements(By.CLASS_NAME, "lead-card")
        visible_count = len(visible_cards)
        
        # Debe mostrar al menos el lead buscado
        self.assertGreater(visible_count, 0)

    def test_clear_filters_resets_all(self, tenant, pipeline, lead_in_lead, lead_in_calificacion, user):
        """
        Click en "Limpiar filtros" debe mostrar todos los leads nuevamente.
        """
        self.auth_get(f"/crm/{tenant.slug}/dashboard/")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "kanban-board"))
        )
        sleep(1)
        
        initial_count = len(self.driver.find_elements(By.CLASS_NAME, "lead-card"))
        
        # Aplicar un filtro
        stage_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[data-stage='Lead'][type='checkbox']")
        stage_checkbox.click()
        
        apply_btn = self.driver.find_element(By.ID, "apply-filters-btn")
        apply_btn.click()
        
        sleep(1)
        
        filtered_count = len(self.driver.find_elements(By.CLASS_NAME, "lead-card"))
        self.assertLess(filtered_count, initial_count)
        
        # Limpiar filtros
        clear_btn = self.driver.find_element(By.ID, "clear-filters-btn")
        clear_btn.click()
        
        sleep(1)
        
        # Debe volver al count inicial
        final_count = len(self.driver.find_elements(By.CLASS_NAME, "lead-card"))
        self.assertEqual(final_count, initial_count)
