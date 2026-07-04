"""Fixtures para tests de la app ingesta."""

import pytest
from ingesta.models import EvolutionInstance, ChatUser, Message
from django.utils import timezone


@pytest.fixture
def evolution_instance(db):
    return EvolutionInstance.objects.create(
        instance_name="default",
        description="Default instance",
        is_active=True,
    )


@pytest.fixture
def chat_user(db):
    return ChatUser.objects.create(
        wa_id="573001234567@c.us",
        name="Juan Perez",
        phone_number="573001234567",
        is_customer=True,
    )


@pytest.fixture
def chat_user2(db):
    return ChatUser.objects.create(
        wa_id="573007654321@c.us",
        name="Maria Gomez",
        phone_number="573007654321",
        is_customer=True,
    )


@pytest.fixture
def text_message(db, chat_user):
    return Message.objects.create(
        external_id="msg_001",
        user=chat_user,
        content="Hola, quiero información",
        from_me=False,
        direction=Message.Direction.INBOUND,
        message_type=Message.MessageType.TEXT,
        timestamp=timezone.now(),
    )


@pytest.fixture
def audio_message(db, chat_user):
    return Message.objects.create(
        external_id="msg_002",
        user=chat_user,
        content="",
        from_me=False,
        direction=Message.Direction.INBOUND,
        message_type=Message.MessageType.AUDIO,
        timestamp=timezone.now(),
    )


@pytest.fixture
def outbound_message(db, chat_user):
    return Message.objects.create(
        external_id="msg_003",
        user=chat_user,
        content="Claro, con gusto te ayudamos",
        from_me=True,
        direction=Message.Direction.OUTBOUND,
        message_type=Message.MessageType.TEXT,
        timestamp=timezone.now(),
    )
