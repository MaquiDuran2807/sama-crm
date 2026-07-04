"""Tests para el servicio de resúmenes (TextSummaryService)."""

from unittest import mock
from datetime import datetime, timedelta
from dateutil import tz

import pytest
from django.test import override_settings
from django.utils import timezone

from ingesta.models import (
    ChatUser, Message, DailyTextSummary, MonthlyTextSummary,
    SummaryExecutionControl,
)
from ingesta.summary_service import TextSummaryService, SummaryResult


@pytest.fixture
def service():
    return TextSummaryService()


@pytest.fixture
def user_with_messages(db, chat_user):
    now = timezone.now()
    for i in range(3):
        Message.objects.create(
            external_id=f"text_{i}",
            user=chat_user,
            content=f"Message {i}",
            from_me=False,
            message_type=Message.MessageType.TEXT,
            timestamp=now - timedelta(hours=i),
        )
    return chat_user


class TestBuildCompactTranscript:
    def test_builds_transcript(self, db, chat_user, service):
        now = timezone.now()
        Message.objects.create(
            external_id="t1", user=chat_user, content="Hola",
            from_me=False, message_type=Message.MessageType.TEXT,
            timestamp=now,
        )
        Message.objects.create(
            external_id="t2", user=chat_user, content="Buenos días",
            from_me=True, message_type=Message.MessageType.TEXT,
            timestamp=now + timedelta(minutes=5),
        )
        messages = list(Message.objects.all().order_by("timestamp"))
        transcript, unresolved = service._build_compact_transcript(messages)
        assert "CLIENTE:" in transcript
        assert "ASESOR:" in transcript

    def test_unresolved_count(self, db, chat_user, service):
        now = timezone.now()
        Message.objects.create(
            external_id="u1", user=chat_user, content="Pregunta",
            from_me=False, message_type=Message.MessageType.TEXT,
            timestamp=now,
        )
        messages = list(Message.objects.all())
        transcript, unresolved = service._build_compact_transcript(messages)
        assert unresolved > 0

    def test_empty_messages_returns_no_data(self, db, service):
        transcript, unresolved = service._build_compact_transcript([])
        assert transcript == "NO_DATA"


class TestSummarizeDayFallback:
    def test_fallback_no_team_messages(self, db, chat_user, service):
        now = timezone.now()
        Message.objects.create(
            external_id="fb1", user=chat_user, content="Hola",
            from_me=False, message_type=Message.MessageType.TEXT,
            timestamp=now,
        )
        messages = list(Message.objects.all().order_by("timestamp"))
        transcript, unresolved = service._build_compact_transcript(messages)
        text, pending = service._build_day_fallback_from_transcript(
            transcript, unresolved,
        )
        assert text != "NO_DATA"
        assert "Cliente" in text

    def test_fallback_empty(self, service):
        text, pending = service._build_day_fallback_from_transcript("", 0)
        assert text == "NO_DATA"


class TestSummarizeDay:
    @mock.patch("ingesta.summary_service.requests.post")
    def test_summarize_day_calls_model(self, mock_post, db, chat_user, service):
        now = timezone.now()
        Message.objects.create(
            external_id="sd1", user=chat_user, content="Hola",
            from_me=False, message_type=Message.MessageType.TEXT,
            timestamp=now,
        )
        Message.objects.create(
            external_id="sd2", user=chat_user, content="Buenos días",
            from_me=True, message_type=Message.MessageType.TEXT,
            timestamp=now + timedelta(minutes=5),
        )
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "response": '{"resumen_corto": "Cliente saludo"}',
            "prompt_eval_count": 10,
            "eval_count": 5,
        }
        messages = list(Message.objects.all().order_by("timestamp"))
        transcript, unresolved = service._build_compact_transcript(messages)
        result = service._summarize_day(
            user=chat_user, target_day=now.date(),
            compact_transcript=transcript, unresolved_count=unresolved,
        )
        assert result.has_data is True
        assert result.text == "Cliente saludo"

    def test_summarize_day_no_data(self, db, chat_user, service):
        result = service._summarize_day(
            user=chat_user, target_day=timezone.now().date(),
            compact_transcript="NO_DATA", unresolved_count=0,
        )
        assert result.has_data is False


class TestProcessUserWindow:
    def test_no_messages_returns_false(self, db, chat_user, service):
        now = timezone.now()
        result = service._process_user_window(
            user=chat_user,
            slot_start=now - timedelta(hours=1),
            slot_end=now,
            exec_log=SummaryExecutionControl.objects.create(
                run_key="test_no_msgs",
                slot_start=now - timedelta(hours=1),
                slot_end=now,
            ),
        )
        assert result is False

    @mock.patch("ingesta.summary_service.requests.post")
    def test_creates_daily_summary(self, mock_post, db, chat_user, service):
        now = timezone.now()
        Message.objects.create(
            external_id="pw1", user=chat_user, content="Hola",
            from_me=True, message_type=Message.MessageType.TEXT,
            timestamp=now,
        )
        Message.objects.create(
            external_id="pw2", user=chat_user, content="Info",
            from_me=False, message_type=Message.MessageType.TEXT,
            timestamp=now + timedelta(minutes=5),
        )
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "response": '{"resumen_corto": "Cliente pidio info"}',
            "prompt_eval_count": 10,
            "eval_count": 5,
        }
        slot_start = now - timedelta(hours=2)
        slot_end = now + timedelta(hours=1)
        exec_log = SummaryExecutionControl.objects.create(
            run_key="test_daily",
            slot_start=slot_start,
            slot_end=slot_end,
        )
        result = service._process_user_window(
            user=chat_user, slot_start=slot_start, slot_end=slot_end,
            exec_log=exec_log,
        )
        assert result is True
        assert DailyTextSummary.objects.filter(user=chat_user).exists()


class TestComputeAccumulationWindow:
    def test_returns_window(self, db, service):
        now = timezone.now()
        slot_start, meta = service.compute_accumulation_window(slot_end=now)
        assert slot_start <= now
        assert "accumulation_cursor_start" in meta


class TestEmptyResult:
    def test_empty_result_has_no_data(self, service):
        result = service._empty_result("NO_DATA")
        assert isinstance(result, SummaryResult)
        assert result.has_data is False
        assert result.text == "NO_DATA"
