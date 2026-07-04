"""Servicios de dominio para la app core.

Este módulo concentra la lógica de negocio pura relacionada con el sitio
web, páginas, secciones y gestión de contenido.
"""

from typing import Any


def get_page_by_slug(tenant: Any, slug: str) -> Any | None:
    """Obtiene una página publicada por su slug.

    Args:
        tenant: Tenant al que pertenece la página.
        slug: Slug de la página.

    Returns:
        Página si existe y está publicada, None en caso contrario.
    """
    from core.domain.models import Page

    return Page.objects.filter(
        tenant=tenant,
        slug=slug,
        status=Page.PageStatus.PUBLISHED,
    ).first()


def get_published_pages(tenant: Any) -> list:
    """Obtiene todas las páginas publicadas de un tenant.

    Args:
        tenant: Tenant del que se obtienen las páginas.

    Returns:
        Lista de páginas publicadas ordenadas por orden.
    """
    from core.domain.models import Page

    return list(
        Page.objects.filter(
            tenant=tenant,
            status=Page.PageStatus.PUBLISHED,
        ).order_by("order", "-created_at")
    )


def get_menu_items(tenant: Any, parent_id: int | None = None) -> list:
    """Obtiene los elementos del menú de navegación.

    Args:
        tenant: Tenant al que pertenece el menú.
        parent_id: ID del elemento padre (None para items raíz).

    Returns:
        Lista de elementos del menú.
    """
    from core.domain.models import MenuItem

    queryset = MenuItem.objects.filter(
        tenant=tenant,
        is_visible=True,
    )

    if parent_id is None:
        queryset = queryset.filter(parent__isnull=True)

    return list(queryset.select_related("page").order_by("order"))


def get_site_config(tenant: Any) -> Any | None:
    """Obtiene la configuración del sitio para un tenant.

    Args:
        tenant: Tenant del que se obtiene la configuración.

    Returns:
        Configuración del sitio o None si no existe.
    """
    from core.domain.models import SiteConfiguration

    return SiteConfiguration.objects.filter(
        tenant=tenant,
        is_published=True,
    ).first()


def create_contact_message(
    tenant: Any,
    name: str,
    email: str,
    message: str,
    phone: str = "",
    subject: str = "",
    ip_address: str | None = None,
) -> Any:
    """Crea un mensaje de contacto.

    Args:
        tenant: Tenant que recibe el mensaje.
        name: Nombre del remitente.
        email: Email del remitente.
        message: Contenido del mensaje.
        phone: Teléfono (opcional).
        subject: Asunto (opcional).
        ip_address: IP del visitante (opcional).

    Returns:
        Instancia de ContactMessage creada.
    """
    from core.domain.models import ContactMessage

    return ContactMessage.objects.create(
        tenant=tenant,
        name=name,
        email=email,
        phone=phone,
        subject=subject,
        message=message,
        ip_address=ip_address,
    )


def get_contact_messages(tenant: Any, status: str | None = None) -> list:
    """Obtiene los mensajes de contacto de un tenant.

    Args:
        tenant: Tenant del que se obtienen los mensajes.
        status: Filtrar por estado (opcional).

    Returns:
        Lista de mensajes de contacto.
    """
    from core.domain.models import ContactMessage

    queryset = ContactMessage.objects.filter(tenant=tenant)

    if status:
        queryset = queryset.filter(status=status)

    return list(queryset)


def count_unread_messages(tenant: Any) -> int:
    """Cuenta los mensajes no leídos de un tenant.

    Args:
        tenant: Tenant del que se cuentan los mensajes.

    Returns:
        Cantidad de mensajes nuevos/no leídos.
    """
    from core.domain.models import ContactMessage

    return ContactMessage.objects.filter(
        tenant=tenant,
        status=ContactMessage.Status.NEW,
    ).count()


def get_page_sections(page: Any) -> list:
    """Obtiene las secciones de una página ordenadas.

    Args:
        page: Página de la que se obtienen las secciones.

    Returns:
        Lista de secciones ordenadas por orden.
    """
    return list(page.sections.all().order_by("order"))