"""Tests para modelos de la app ingesta."""

import pytest
from django.db import IntegrityError
from django.utils import timezone
from ingesta.models import (
    EvolutionInstance, ChatUser, Message, UserInteraction,
    IngestionControl, SummaryExecutionControl, DailyTextSummary,
    MonthlyTextSummary,
)


class TestEvolutionInstance:
    def test_create_instance(self, db):
        inst = EvolutionInstance.objects.create(
            instance_name="test-instance",
            description="Test",
        )
        assert inst.instance_name == "test-instance"
        assert inst.is_active is True
        assert str(inst) == "test-instance ✓"

    def test_unique_name(self, db, evolution_instance):
        with pytest.raises(IntegrityError):
            EvolutionInstance.objects.create(instance_name="default")

    def test_ordering(self, db):
        b = EvolutionInstance.objects.create(instance_name="b-instance")
        a = EvolutionInstance.objects.create(instance_name="a-instance")
        qs = EvolutionInstance.objects.all()
        assert list(qs) == [a, b]


class TestChatUser:
    def test_create_user(self, db):
        user = ChatUser.objects.create(
            wa_id="573001234567@c.us",
            name="Juan Perez",
            phone_number="573001234567",
        )
        assert user.wa_id == "573001234567@c.us"
        assert user.is_customer is True

    def test_unique_wa_id(self, db, chat_user):
        with pytest.raises(IntegrityError):
            ChatUser.objects.create(wa_id="573001234567@c.us")

    def test_display_label_with_name_and_phone(self, db):
        user = ChatUser.objects.create(
            wa_id="wa_001", name="Ana", phone_number="573009999999",
        )
        assert "Ana" in user.display_label()
        assert "573009999999" in user.display_label()

    def test_display_label_fallback_to_wa_id(self, db):
        user = ChatUser.objects.create(wa_id="wa_only_001")
        assert user.display_label() == "wa_only_001"

    def test_str(self, db):
        user = ChatUser.objects.create(wa_id="wa_str", name="Carlos")
        assert str(user) == user.display_label()


class TestMessage:
    def test_create_text_message(self, db, chat_user):
        msg = Message.objects.create(
            external_id="ext_001",
            user=chat_user,
            content="Hola mundo",
            message_type=Message.MessageType.TEXT,
            direction=Message.Direction.INBOUND,
            timestamp=timezone.now(),
        )
        assert msg.external_id == "ext_001"
        assert msg.is_media_message is False

    def test_unique_external_id(self, db, text_message):
        with pytest.raises(IntegrityError):
            Message.objects.create(
                external_id="msg_001",
                user=text_message.user,
                content="Duplicado",
                timestamp=timezone.now(),
            )

    def test_is_media_message_audio(self, db, audio_message):
        assert audio_message.is_media_message is True

    def test_is_media_message_text(self, db, text_message):
        assert text_message.is_media_message is False

    def test_media_state_non_media(self, db, text_message):
        assert text_message.media_state == "NON_MEDIA"

    def test_media_state_no_media(self, db, audio_message):
        assert audio_message.media_state == "NO_MEDIA"

    def test_media_state_available(self, db, chat_user):
        msg = Message.objects.create(
            external_id="ext_media",
            user=chat_user,
            content="",
            message_type=Message.MessageType.AUDIO,
            media_file="ingesta/audio/test.wav",
            timestamp=timezone.now(),
        )
        assert msg.media_state == "AVAILABLE"

    def test_has_encrypted_media_file(self, db, chat_user):
        msg = Message.objects.create(
            external_id="ext_enc",
            user=chat_user,
            message_type=Message.MessageType.AUDIO,
            media_file="ingesta/audio/test.enc",
            timestamp=timezone.now(),
        )
        assert msg.has_encrypted_media_file is True
        assert msg.has_usable_media_file is False

    def test_has_usable_media_file(self, db, chat_user):
        msg = Message.objects.create(
            external_id="ext_usable",
            user=chat_user,
            message_type=Message.MessageType.AUDIO,
            media_file="ingesta/audio/test.wav",
            timestamp=timezone.now(),
        )
        assert msg.has_usable_media_file is True

    def test_ordering(self, db, chat_user):
        old = Message.objects.create(
            external_id="old_msg", user=chat_user,
            timestamp=timezone.now() - timezone.timedelta(hours=2),
            content="old",
        )
        new = Message.objects.create(
            external_id="new_msg", user=chat_user,
            timestamp=timezone.now(),
            content="new",
        )
        qs = Message.objects.all()
        assert list(qs) == [new, old]

    def test_str(self, db, text_message):
        expected = f"{text_message.external_id} - {text_message.message_type}"
        assert str(text_message) == expected


class TestUserInteraction:
    def test_create_interaction(self, db, chat_user):
        interaction = UserInteraction.objects.create(
            user=chat_user,
            interaction_type=UserInteraction.InteractionType.CALL,
            occurred_at=timezone.now(),
        )
        assert interaction.interaction_type == "call"
        assert interaction.direction == UserInteraction.Direction.OUTBOUND

    def test_str(self, db, chat_user):
        now = timezone.now()
        interaction = UserInteraction.objects.create(
            user=chat_user,
            occurred_at=now,
        )
        expected = f"{chat_user.id} call {now.isoformat()}"
        assert str(interaction) == expected


class TestIngestionControl:
    def test_create_control(self, db, evolution_instance):
        control = IngestionControl.objects.create(
            instance=evolution_instance,
            last_sync_timestamp=timezone.now(),
        )
        assert control.instance == evolution_instance
        assert str(control).startswith("default @")

    def test_one_to_one(self, db, evolution_instance):
        IngestionControl.objects.create(
            instance=evolution_instance,
            last_sync_timestamp=timezone.now(),
        )
        with pytest.raises(IntegrityError):
            IngestionControl.objects.create(
                instance=evolution_instance,
                last_sync_timestamp=timezone.now(),
            )


class TestSummaryExecutionControl:
    def test_create_execution(self, db):
        now = timezone.now()
        exec_log = SummaryExecutionControl.objects.create(
            run_key="test_run_001",
            slot_start=now - timezone.timedelta(hours=1),
            slot_end=now,
        )
        assert exec_log.status == SummaryExecutionControl.Status.RUNNING
        assert str(exec_log) == "test_run_001 [running]"

    def test_unique_run_key(self, db):
        now = timezone.now()
        SummaryExecutionControl.objects.create(
            run_key="unique_key",
            slot_start=now,
            slot_end=now,
        )
        with pytest.raises(IntegrityError):
            SummaryExecutionControl.objects.create(
                run_key="unique_key",
                slot_start=now,
                slot_end=now,
            )


class TestDailyTextSummary:
    def test_create_summary(self, db, chat_user):
        summary = DailyTextSummary.objects.create(
            user=chat_user,
            summary_date=timezone.now().date(),
            text="Resumen de prueba",
            has_data=True,
        )
        assert summary.text == "Resumen de prueba"
        assert str(summary).startswith(f"{chat_user.id} ")

    def test_unique_user_date(self, db, chat_user):
        today = timezone.now().date()
        DailyTextSummary.objects.create(
            user=chat_user, summary_date=today, text="First",
        )
        with pytest.raises(IntegrityError):
            DailyTextSummary.objects.create(
                user=chat_user, summary_date=today, text="Second",
            )


class TestMonthlyTextSummary:
    def test_create_monthly(self, db, chat_user):
        monthly = MonthlyTextSummary.objects.create(
            user=chat_user,
            year=2026,
            month=7,
            text="Resumen mensual",
            has_data=True,
        )
        assert monthly.revision == 1
        assert monthly.is_current is True
        assert str(monthly) == f"{chat_user.id} 2026-07 r1"
