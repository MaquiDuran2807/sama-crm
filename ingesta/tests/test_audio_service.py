"""Tests para el servicio de audio (AudioBriefingService)."""

from unittest import mock
from datetime import datetime

import pytest
from django.test import override_settings
from django.utils import timezone

from ingesta.models import ChatUser, Message


class TestToSpokenPendingText:
    def test_image_message(self, db, chat_user):
        from ingesta.audio_service import AudioBriefingService
        service = AudioBriefingService.__new__(AudioBriefingService)
        msg = Message.objects.create(
            external_id="img_001", user=chat_user,
            message_type=Message.MessageType.IMAGE,
            timestamp=timezone.now(),
        )
        text = service._to_spoken_pending_text(msg)
        assert "imágenes" in text

    def test_text_message(self, db, chat_user):
        from ingesta.audio_service import AudioBriefingService
        service = AudioBriefingService.__new__(AudioBriefingService)
        msg = Message.objects.create(
            external_id="txt_001", user=chat_user,
            content="Necesito información",
            message_type=Message.MessageType.TEXT,
            timestamp=timezone.now(),
        )
        text = service._to_spoken_pending_text(msg)
        assert text == "Necesito información"

    def test_audio_message(self, db, chat_user):
        from ingesta.audio_service import AudioBriefingService
        service = AudioBriefingService.__new__(AudioBriefingService)
        msg = Message.objects.create(
            external_id="aud_001", user=chat_user,
            message_type=Message.MessageType.AUDIO,
            timestamp=timezone.now(),
        )
        text = service._to_spoken_pending_text(msg)
        assert "audio" in text

    def test_empty_content_message(self, db, chat_user):
        from ingesta.audio_service import AudioBriefingService
        service = AudioBriefingService.__new__(AudioBriefingService)
        msg = Message.objects.create(
            external_id="emp_001", user=chat_user,
            message_type=Message.MessageType.TEXT,
            content="",
            timestamp=timezone.now(),
        )
        text = service._to_spoken_pending_text(msg)
        assert "mensaje" in text


class TestCleanSpokenName:
    def test_removes_whatsapp_suffix(self):
        from ingesta.audio_service import AudioBriefingService
        result = AudioBriefingService._clean_spoken_name("Juan@s.whatsapp.net")
        assert result == "Juan"

    def test_removes_phone_parenthesis(self):
        from ingesta.audio_service import AudioBriefingService
        result = AudioBriefingService._clean_spoken_name("Juan (573001234567)")
        assert result == "Juan"

    def test_fallback_when_empty(self):
        from ingesta.audio_service import AudioBriefingService
        result = AudioBriefingService._clean_spoken_name("", fallback="cliente")
        assert result == "cliente"


class TestTruncate:
    def test_truncates_long_text(self):
        from ingesta.audio_service import AudioBriefingService
        result = AudioBriefingService._truncate("A" * 100, 10)
        assert len(result) == 10
        assert result.endswith("…")

    def test_short_text_unchanged(self):
        from ingesta.audio_service import AudioBriefingService
        result = AudioBriefingService._truncate("Short", 50)
        assert result == "Short"


class TestClientPriorityKey:
    def test_no_response_first(self):
        from ingesta.audio_service import AudioBriefingService
        key = AudioBriefingService._client_priority_key({})
        assert key[0] == 0

    def test_with_response(self):
        from ingesta.audio_service import AudioBriefingService
        from datetime import datetime, timezone
        key = AudioBriefingService._client_priority_key({
            "last_our_response_ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
        })
        assert key[0] == 1


class TestNormalizePendingPhrase:
    def test_image_phrase(self):
        from ingesta.audio_service import AudioBriefingService
        result = AudioBriefingService._normalize_pending_phrase(
            "El cliente envió una o varias imágenes por revisar"
        )
        assert result.endswith(".")

    def test_text_preserved(self):
        from ingesta.audio_service import AudioBriefingService
        result = AudioBriefingService._normalize_pending_phrase("Hola, necesito ayuda")
        assert result == "Hola, necesito ayuda"
