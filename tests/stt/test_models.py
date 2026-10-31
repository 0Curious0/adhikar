from adhikar.stt.models import STTEventType, STTStreamEvent


def test_from_payload_parses_transcript_event():
    payload = {
        "type": "transcript",
        "timestamp": "2024-01-15T10:30:05.987Z",
        "text": "Hello, how are you today?",
        "audio_duration_ms": 2340,
        "segment_id": "req-abc-seg-1",
        "segment_index": 1,
        "latency": 320,
        "detected_language_code": "en-IN",
    }

    event = STTStreamEvent.from_payload(payload)

    assert event.type == STTEventType.TRANSCRIPT
    assert event.text == "Hello, how are you today?"
    assert event.segment_id == "req-abc-seg-1"
    assert event.segment_index == 1
    assert event.audio_duration_ms == 2340
    assert event.latency_ms == 320
    assert event.raw == payload


def test_from_payload_parses_connected_event_with_no_transcript_fields():
    payload = {
        "type": "connected",
        "message": "STT service ready",
        "timestamp": "2024-01-15T10:30:00.000Z",
        "config": {"sample_rate": 16000, "chunk_size": 512},
    }

    event = STTStreamEvent.from_payload(payload)

    assert event.type == STTEventType.CONNECTED
    assert event.text is None
    assert event.segment_id is None
    assert event.segment_index is None
    assert event.audio_duration_ms is None
    assert event.latency_ms is None
    assert event.raw == payload


def test_from_payload_parses_error_event():
    payload = {
        "type": "error",
        "timestamp": "2024-01-15T10:30:10.000Z",
        "message": "STT engine failed to initialize",
    }

    event = STTStreamEvent.from_payload(payload)

    assert event.type == STTEventType.ERROR
    assert event.raw == payload
