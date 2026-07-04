"""Factory Boy factories for the ingesta app.

Provides factories for EvolutionInstance, ChatUser, Message,
UserInteraction, DailyTextSummary, MonthlyTextSummary,
IngestionControl, and SummaryExecutionControl.
"""

from datetime import timedelta

import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from ingesta.models import (
    EvolutionInstance, ChatUser, Message,
    UserInteraction, DailyTextSummary, MonthlyTextSummary,
    IngestionControl, SummaryExecutionControl,
)


class EvolutionInstanceFactory(DjangoModelFactory):
    class Meta:
        model = EvolutionInstance
        django_get_or_create = ("instance_name",)

    instance_name = factory.Sequence(lambda n: f"instance-{n}")
    description = factory.Faker("sentence")
    is_active = True


class ChatUserFactory(DjangoModelFactory):
    class Meta:
        model = ChatUser
        django_get_or_create = ("wa_id",)

    wa_id = factory.Sequence(lambda n: f"57{n:010d}@c.us")
    name = factory.Faker("name")
    phone_number = factory.Sequence(lambda n: f"57{n:010d}")
    is_customer = True
    last_interaction = factory.LazyFunction(timezone.now)


class MessageFactory(DjangoModelFactory):
    class Meta:
        model = Message
        django_get_or_create = ("external_id",)

    external_id = factory.Sequence(lambda n: f"msg_{n:06d}")
    user = factory.SubFactory(ChatUserFactory)
    content = factory.Faker("sentence")
    from_me = False
    direction = Message.Direction.INBOUND.value
    message_type = Message.MessageType.TEXT.value
    timestamp = factory.LazyFunction(timezone.now)
    raw_data = {}
    chat_jid = ""
    sender_wa_id = ""
    recipient_wa_id = ""
    quoted_external_id = ""
    media_url = ""
    media_mime_type = ""
    processed = False


class UserInteractionFactory(DjangoModelFactory):
    class Meta:
        model = UserInteraction

    user = factory.SubFactory(ChatUserFactory)
    interaction_type = UserInteraction.InteractionType.CALL.value
    from_me = True
    direction = Message.Direction.OUTBOUND.value
    occurred_at = factory.LazyFunction(timezone.now)
    source = "csv"
    raw_data = {}


class IngestionControlFactory(DjangoModelFactory):
    class Meta:
        model = IngestionControl

    instance = factory.SubFactory(EvolutionInstanceFactory)
    last_sync_timestamp = factory.LazyFunction(timezone.now)


class SummaryExecutionControlFactory(DjangoModelFactory):
    class Meta:
        model = SummaryExecutionControl
        django_get_or_create = ("run_key",)

    run_key = factory.Sequence(lambda n: f"run-{n}")
    slot_start = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))
    slot_end = factory.LazyFunction(timezone.now)
    status = SummaryExecutionControl.Status.COMPLETED.value


class DailyTextSummaryFactory(DjangoModelFactory):
    class Meta:
        model = DailyTextSummary

    user = factory.SubFactory(ChatUserFactory)
    summary_date = factory.LazyFunction(lambda: timezone.now().date())
    text = factory.Faker("paragraph")
    has_data = True
    pending_items = []
    mentioned_people = []
    deadlines = []
    payment_promises = []


class MonthlyTextSummaryFactory(DjangoModelFactory):
    class Meta:
        model = MonthlyTextSummary

    user = factory.SubFactory(ChatUserFactory)
    year = factory.LazyFunction(lambda: timezone.now().year)
    month = factory.LazyFunction(lambda: timezone.now().month)
    text = factory.Faker("paragraph")
    has_data = True
    pending_items = []
    mentioned_people = []
    deadlines = []
    payment_promises = []
