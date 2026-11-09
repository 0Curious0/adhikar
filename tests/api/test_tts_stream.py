import time
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from adhikar.api.app import app
from adhikar.api.routes import get_tts_provider_ws
from adhikar.api.tts_stream import DEFAULT_VOICE
from adhikar.tts.models import TTSEventType, TTSStreamEvent


class FakeTTSStream:
    """One per `stream()` call — mirrors a fresh Timbre connection being opened per reply (see
    adhikar.api.tts_stream), unlike the single-shared-session shape this fake used to have."""

    def __init__(self, events: list[TTSStreamEvent]):
        self._events = events
        self.sent_texts: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent_texts.append(text)

    async def events(self):
        for event in self._events:
            yield event


class FakeTTSProvider:
    def __init__(self, event_batches: list[list[TTSStreamEvent]]):
        self._remaining_batches = list(event_batches)
        self.streams: list[FakeTTSStream] = []
        self.stream_calls: list[dict] = []

    @asynccontextmanager
    async def stream(self, *, language_code: str, voice: str, speed=1.0, audio_config=None):
        self.stream_calls.append({"language_code": language_code, "voice": voice, "audio_config": audio_config})
        batch = self._remaining_batches.pop(0) if self._remaining_batches else []
        tts_stream = FakeTTSStream(batch)
        self.streams.append(tts_stream)
        yield tts_stream


def _connect(provider: FakeTTSProvider, language_code: str = "hi-IN"):
    app.dependency_overrides[get_tts_provider_ws] = lambda: provider
    client = TestClient(app)
    return client.websocket_connect(f"/tts/stream?language_code={language_code}")


def test_relays_audio_chunks_for_one_reply():
    batches = [
        [
            TTSStreamEvent(type=TTSEventType.AUDIO, raw={}, audio=b"chunk1"),
            TTSStreamEvent(type=TTSEventType.AUDIO, raw={}, audio=b"chunk2"),
            TTSStreamEvent(type=TTSEventType.COMPLETE, raw={}),
        ]
    ]
    provider = FakeTTSProvider(batches)

    try:
        with _connect(provider) as websocket:
            websocket.send_text("aap patr hain")
            first = websocket.receive_bytes()
            second = websocket.receive_bytes()
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert first == b"chunk1"
    assert second == b"chunk2"


def test_passes_language_code_and_uses_default_voice():
    batches = [[TTSStreamEvent(type=TTSEventType.COMPLETE, raw={})]]
    provider = FakeTTSProvider(batches)

    try:
        with _connect(provider, language_code="ta-IN") as websocket:
            websocket.send_text("hello")
            websocket.close()
            time.sleep(0.1)
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert provider.stream_calls[0]["language_code"] == "ta-IN"
    assert provider.stream_calls[0]["voice"] == DEFAULT_VOICE
    assert provider.stream_calls[0]["audio_config"].container == "raw"


def test_forwards_client_text_to_send_text():
    batches = [[TTSStreamEvent(type=TTSEventType.COMPLETE, raw={})]]
    provider = FakeTTSProvider(batches)

    try:
        with _connect(provider) as websocket:
            websocket.send_text("aap patr hain")
            websocket.close()
            time.sleep(0.1)
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert provider.streams[0].sent_texts == ["aap patr hain"]


def test_handles_multiple_replies_opens_a_fresh_upstream_connection_each_time():
    # The regression this guards against: Timbre's realtime endpoint does not reliably handle
    # multiple sequential requests over one connection (see adhikar.api.tts_stream's docstring) —
    # every reply must open its own `tts_provider.stream()`, not share one across the session.
    batches = [
        [TTSStreamEvent(type=TTSEventType.AUDIO, raw={}, audio=b"reply-one"), TTSStreamEvent(type=TTSEventType.COMPLETE, raw={})],
        [TTSStreamEvent(type=TTSEventType.AUDIO, raw={}, audio=b"reply-two"), TTSStreamEvent(type=TTSEventType.COMPLETE, raw={})],
    ]
    provider = FakeTTSProvider(batches)

    try:
        with _connect(provider) as websocket:
            websocket.send_text("first reply")
            first = websocket.receive_bytes()
            websocket.send_text("second reply")
            second = websocket.receive_bytes()
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert first == b"reply-one"
    assert second == b"reply-two"
    assert len(provider.stream_calls) == 2
    assert provider.streams[0].sent_texts == ["first reply"]
    assert provider.streams[1].sent_texts == ["second reply"]


def test_stops_relaying_on_error_event_without_hanging():
    batches = [
        [
            TTSStreamEvent(type=TTSEventType.AUDIO, raw={}, audio=b"partial"),
            TTSStreamEvent(type=TTSEventType.ERROR, raw={}, message="synthesis failed"),
        ]
    ]
    provider = FakeTTSProvider(batches)

    try:
        with _connect(provider) as websocket:
            websocket.send_text("hello")
            partial = websocket.receive_bytes()
            # Without this, the client sent text and gets nothing back at all on failure —
            # indistinguishable from "still synthesizing." See adhikar.api.tts_stream.
            error_message = websocket.receive_json()
            websocket.close()
            time.sleep(0.1)
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert partial == b"partial"
    assert error_message == {"type": "error", "message": "synthesis failed"}


def test_client_disconnect_tears_down_cleanly_mid_session():
    provider = FakeTTSProvider([[TTSStreamEvent(type=TTSEventType.COMPLETE, raw={})]])

    try:
        with _connect(provider) as websocket:
            websocket.close()
            time.sleep(0.1)
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert provider.stream_calls == []
