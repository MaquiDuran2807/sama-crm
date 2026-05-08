"""Servicio de sincronización de contactos entre ingesta y CRM.

Este módulo orquesta la creación/actualización de un ChatUser (app ingesta)
y un Contact (app crm) a partir de un número de teléfono y nombre,
garantizando que ambas entidades queden vinculadas al mismo tenant y número.
"""

from __future__ import annotations

from typing import Any

from crm.domain.models import Contact
from ingesta.models import ChatUser


def sync_contact_from_whatsapp(
    tenant: Any,
    phone_number: str,
    name: str = "",
) -> Contact:
    """Encuentra o crea un ChatUser (ingesta) y un Contact (crm) para un número.

    1. Busca un ChatUser por ``phone_number``. Si no existe, lo crea.
       Si existe y se proporciona un nombre no vacío, actualiza el nombre.
    2. Busca un Contact por ``tenant`` + ``phone_number``. Si no existe, lo crea.
       Si existe y su ``full_name`` está vacío, lo actualiza con el nombre.
    3. Retorna el Contact (CRM).

    Args:
        tenant: Instancia del tenant al que pertenece el contacto.
        phone_number: Número de teléfono del contacto.
        name: Nombre del contacto (opcional).

    Returns:
        Instancia de ``Contact`` creada o actualizada.
    """
    phone = phone_number.strip()
    name = name.strip()

    # 1. ChatUser (ingesta)
    chat_user, created = ChatUser.objects.get_or_create(
        phone_number=phone,
        defaults={
            "name": name or phone,
            "wa_id": phone,
        },
    )
    if not created and name and chat_user.name != name:
        chat_user.name = name
        chat_user.save(update_fields=["name"])

    # 2. Contact (crm)
    contact, created = Contact.objects.get_or_create(
        tenant=tenant,
        phone_number=phone,
        defaults={
            "full_name": name or chat_user.name,
        },
    )
    if not created and not contact.full_name and (name or chat_user.name):
        contact.full_name = name or chat_user.name
        contact.save(update_fields=["full_name"])

    return contact
