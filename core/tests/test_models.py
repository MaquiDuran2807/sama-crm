"""Tests para modelos de la app core."""

import pytest
from django.utils import timezone
from core.domain.models import Page, Section, MenuItem, SiteConfiguration, ContactMessage


class TestSiteConfiguration:
    def test_create_config(self, db, tenant):
        config = SiteConfiguration.objects.create(
            tenant=tenant,
            hero_title="Welcome",
            primary_color="#2563eb",
        )
        assert config.tenant == tenant
        assert config.hero_title == "Welcome"
        assert config.is_published is True

    def test_str(self, db, tenant):
        config = SiteConfiguration.objects.create(tenant=tenant)
        assert str(config) == f"Configuración - {tenant.name}"

    def test_one_to_one_tenant(self, db, tenant):
        SiteConfiguration.objects.create(tenant=tenant)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            SiteConfiguration.objects.create(tenant=tenant)


class TestPage:
    def test_create_page(self, db, tenant):
        page = Page.objects.create(
            tenant=tenant,
            title="Inicio",
            slug="inicio",
            status=Page.PageStatus.PUBLISHED,
        )
        assert page.title == "Inicio"
        assert page.slug == "inicio"
        assert page.status == "published"

    def test_unique_tenant_slug(self, db, tenant):
        Page.objects.create(tenant=tenant, title="A", slug="test")
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Page.objects.create(tenant=tenant, title="B", slug="test")

    def test_str(self, db, tenant):
        page = Page.objects.create(tenant=tenant, title="About", slug="about")
        assert str(page) == f"About ({tenant.name})"

    def test_default_status_is_draft(self, db, tenant):
        page = Page.objects.create(tenant=tenant, title="Draft", slug="draft")
        assert page.status == Page.PageStatus.DRAFT


class TestSection:
    def test_create_section(self, db, tenant):
        page = Page.objects.create(tenant=tenant, title="Page", slug="page")
        section = Section.objects.create(
            page=page,
            section_type=Section.SectionType.HERO,
            title="Hero Title",
        )
        assert section.section_type == "hero"
        assert str(section).startswith("Hero/Banner")

    def test_ordering(self, db, tenant):
        page = Page.objects.create(tenant=tenant, title="Page", slug="page")
        s1 = Section.objects.create(page=page, section_type=Section.SectionType.TEXT, order=2)
        s2 = Section.objects.create(page=page, section_type=Section.SectionType.CTA, order=1)
        sections = list(page.sections.all())
        assert sections == [s2, s1]


class TestMenuItem:
    def test_create_menu_item(self, db, tenant):
        item = MenuItem.objects.create(
            tenant=tenant,
            title="Home",
            url="/",
        )
        assert item.title == "Home"
        assert item.is_visible is True

    def test_str(self, db, tenant):
        item = MenuItem.objects.create(tenant=tenant, title="Services", url="/services")
        assert str(item) == f"Services ({tenant.name})"

    def test_parent_child(self, db, tenant):
        parent = MenuItem.objects.create(tenant=tenant, title="Parent", url="#")
        child = MenuItem.objects.create(tenant=tenant, title="Child", url="#", parent=parent)
        assert child.parent == parent


class TestContactMessage:
    def test_create_message(self, db, tenant):
        msg = ContactMessage.objects.create(
            tenant=tenant,
            name="Juan Perez",
            email="juan@test.com",
            message="Hola, quiero info",
        )
        assert msg.status == ContactMessage.Status.NEW
        assert str(msg) == f"Mensaje de {msg.name} - {tenant.name}"

    def test_default_status(self, db, tenant):
        msg = ContactMessage.objects.create(
            tenant=tenant, name="A", email="a@b.com", message="Test",
        )
        assert msg.status == "new"
