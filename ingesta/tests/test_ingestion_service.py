"""Tests para el servicio de ingesta (IngestionService)."""

from unittest import mock
from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.test import override_settings
from ingesta.models import Message, ChatUser, IngestionControl, EvolutionInstance


@pytest.fixture
def mock_evolution_response():
    return {
        "messages": {
            "records": [
                {
                    "id": "ext_001",
                    "key": {
                        "remoteJid": "573001234567@c.us",
                        "fromMe": False,
                        "id": "ext_001",
                    },
                    "message": {"conversation": "Hola"},
                    "messageTimestamp": int(datetime.now(dt_timezone.utc).timestamp()),
                    "pushName": "Juan",
                },
                {
                    "id": "ext_002",
                    "key": {
                        "remoteJid": "573001234567@c.us",
                        "fromMe": False,
                        "id": "ext_002",
                    },
                    "message": {"conversation": "Info"},
                    "messageTimestamp": int(datetime.now(dt_timezone.utc).timestamp()),
                    "pushName": "Juan",
                },
            ],
            "currentPage": 1,
            "pages": 1,
        }
    }


@pytest.fixture
def mock_empty_response():
    return {"messages": {"records": [], "currentPage": 1, "pages": 1}}


class TestIngestionServiceSync:
    @override_settings(EVOLUTION_BASE_URL="http://fake-evolution.test")
    def test_sync_creates_messages(self, db, evolution_instance, mock_evolution_response):
        from ingesta.services import IngestionService
        service = IngestionService(instance_name="default")
        with mock.patch.object(service, "_fetch_messages_page", return_value=mock_evolution_response):
            result = service.sync_messages()
        assert result["inserted"] == 2
        assert Message.objects.count() == 2

    @override_settings(EVOLUTION_BASE_URL="http://fake-evolution.test")
    def test_deduplication_by_external_id(self, db, evolution_instance, mock_evolution_response):
        from ingesta.services import IngestionService
        ChatUser.objects.create(wa_id="573001234567@c.us", name="Juan")
        Message.objects.create(
            external_id="ext_001",
            user=ChatUser.objects.first(),
            content="Existing",
            timestamp=datetime.now(dt_timezone.utc),
        )
        service = IngestionService(instance_name="default")
        with mock.patch.object(service, "_fetch_messages_page", return_value=mock_evolution_response):
            result = service.sync_messages()
        assert result["inserted"] == 1
        assert result["deduplicated"] == 1

    @override_settings(EVOLUTION_BASE_URL="http://fake-evolution.test")
    def test_no_new_messages_returns_empty(self, db, evolution_instance, mock_empty_response):
        from ingesta.services import IngestionService
        service = IngestionService(instance_name="default")
        with mock.patch.object(service, "_fetch_messages_page", return_value=mock_empty_response):
            result = service.sync_messages()
        assert result["inserted"] == 0
        assert result["fetched"] == 0

    @override_settings(EVOLUTION_BASE_URL="http://fake-evolution.test")
    def test_invalid_instance_raises_error(self, db):
        from ingesta.services import IngestionService
        service = IngestionService(instance_name="nonexistent")
        with pytest.raises(ValueError, match="no encontrada"):
            service.sync_messages()


class TestIngestionServiceHelpers:
    def test_extract_page_bundle_from_dict(self):
        from ingesta.services import IngestionService
        payload = {
            "messages": {
                "records": [{"id": "1"}, {"id": "2"}],
                "currentPage": 1,
                "pages": 1,
            }
        }
        records, page, total = IngestionService._extract_page_bundle(payload)
        assert len(records) == 2
        assert page == 1

    def test_extract_page_bundle_from_list(self):
        from ingesta.services import IngestionService
        records, page, total = IngestionService._extract_page_bundle([{"id": "1"}])
        assert len(records) == 1

    def test_extract_page_bundle_empty(self):
        from ingesta.services import IngestionService
        records, page, total = IngestionService._extract_page_bundle({})
        assert records == []

    def test_build_external_id_from_id(self):
        from ingesta.services import IngestionService
        result = IngestionService._build_external_id({"id": "ext_123"})
        assert result == "ext_123"

    def test_build_external_id_from_key(self):
        from ingesta.services import IngestionService
        result = IngestionService._build_external_id({"key": {"id": "key_id"}})
        assert result == "key_id"

    def test_extract_content_conversation(self):
        from ingesta.services import IngestionService
        row = {"message": {"conversation": "Hola mundo"}}
        assert IngestionService._extract_content(row) == "Hola mundo"

    def test_extract_content_extended_text(self):
        from ingesta.services import IngestionService
        row = {"message": {"extendedTextMessage": {"text": "Texto largo"}}}
        assert IngestionService._extract_content(row) == "Texto largo"

    def test_extract_content_image_with_caption(self):
        from ingesta.services import IngestionService
        row = {"message": {"imageMessage": {"caption": "Foto de prueba"}}}
        assert IngestionService._extract_content(row) == "Foto de prueba"

    def test_extract_content_image_without_caption(self):
        from ingesta.services import IngestionService
        row = {"message": {"imageMessage": {}}}
        assert IngestionService._extract_content(row) == "[image]"

    def test_extract_content_audio(self):
        from ingesta.services import IngestionService
        row = {"message": {"audioMessage": {}}}
        assert IngestionService._extract_content(row) == "[audio]"

    def test_extract_type_text(self):
        from ingesta.services import IngestionService
        assert IngestionService._extract_type({"messageType": "text"}) == Message.MessageType.TEXT

    def test_extract_type_audio(self):
        from ingesta.services import IngestionService
        assert IngestionService._extract_type({"type": "audioMessage"}) == Message.MessageType.AUDIO

    def test_extract_type_image(self):
        from ingesta.services import IngestionService
        assert IngestionService._extract_type({"messageType": "imageMessage"}) == Message.MessageType.IMAGE

    def test_guess_media_extension_from_url(self):
        from ingesta.services import IngestionService
        ext = IngestionService._guess_media_extension("https://example.com/audio.ogg", "")
        assert ext == ".ogg"

    def test_guess_media_extension_from_mime(self):
        from ingesta.services import IngestionService
        ext = IngestionService._guess_media_extension("https://example.com/file", "audio/mpeg")
        assert ext == ".mp3"

    def test_guess_media_extension_fallback(self):
        from ingesta.services import IngestionService
        ext = IngestionService._guess_media_extension("https://example.com/file", "application/octet-stream")
        assert ext == ".bin"

    def test_extract_from_me_true(self):
        from ingesta.services import IngestionService
        assert IngestionService._extract_from_me({"key": {"fromMe": True}}) is True

    def test_extract_from_me_false(self):
        from ingesta.services import IngestionService
        assert IngestionService._extract_from_me({"key": {"fromMe": False}}) is False

    def test_is_generic_self_label(self):
        from ingesta.services import IngestionService
        assert IngestionService._is_generic_self_label("you") is True
        assert IngestionService._is_generic_self_label("Juan") is False

    def test_is_name_like_number(self):
        from ingesta.services import IngestionService
        assert IngestionService._is_name_like_number("573001234567") is True
        assert IngestionService._is_name_like_number("Juan") is False

    def test_sanitize_contact_name(self):
        from ingesta.services import IngestionService
        assert IngestionService._sanitize_contact_name("Juan", False) == "Juan"
        assert IngestionService._sanitize_contact_name("you", True) == ""
        assert IngestionService._sanitize_contact_name("573001234567", False) == ""
