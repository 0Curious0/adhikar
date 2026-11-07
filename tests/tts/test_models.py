import base64

from adhikar.tts.models import TTSEventType, TTSStreamEvent


def test_from_payload_parses_audio_event():
    audio_bytes = b"fake-audio-bytes"
    payload = {
        "type": "audio",
        "request_id": "req_abc123",
        "data": {
            "chunk_index": 3,
            "audio": base64.b64encode(audio_bytes).decode(),
            "is_final": False,
        },
    }

    event = TTSStreamEvent.from_payload(payload)

    assert event.type == TTSEventType.AUDIO
    assert event.request_id == "req_abc123"
    assert event.chunk_index == 3
    assert event.audio == audio_bytes
    assert event.is_final is False
    assert event.raw == payload


def test_from_payload_parses_start_event_with_no_audio_fields():
    payload = {
        "type": "start",
        "request_id": "req_abc123",
    }

    event = TTSStreamEvent.from_payload(payload)

    assert event.type == TTSEventType.START
    assert event.request_id == "req_abc123"
    assert event.chunk_index is None
    assert event.audio is None
    assert event.is_final is None
    assert event.raw == payload


def test_from_payload_parses_complete_event():
    payload = {
        "type": "complete",
        "request_id": "req_abc123",
        "data": {"is_final": True},
    }

    event = TTSStreamEvent.from_payload(payload)

    assert event.type == TTSEventType.COMPLETE
    assert event.is_final is True
    assert event.audio is None
    assert event.raw == payload


def test_from_payload_parses_error_event():
    payload = {
        "type": "error",
        "message": "Timbre synthesis failed",
    }

    event = TTSStreamEvent.from_payload(payload)

    assert event.type == TTSEventType.ERROR
    assert event.message == "Timbre synthesis failed"
    assert event.raw == payload
