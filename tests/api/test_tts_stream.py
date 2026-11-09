import time
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from adhikar.api.app import app
from adhikar.api.routes import get_tts_provider_ws
from adhikar.api.tts_stream import DEFAULT_VOICE
from adhikar.tts.models import TTSEventType, TTSStreamEvent


class FakeTTSStream:
    def __init__(self, event_batches: list[list[TTSStreamEvent]]):
        self._event_batches = event_batches
        self.sent_texts: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent_texts.append(text)

    async def events(self):
        for batch in self._event_batches:
            for event in batch:
                yield event


class FakeTTSProvider:
    def __init__(self, tts_stream: FakeTTSStream):
        self._tts_stream = tts_stream
        self.stream_calls: list[dict] = []

    @asynccontextmanager
    async def stream(self, *, language_code: str, voice: str, speed=1.0, audio_config=None):
        self.stream_calls.append({"language_code": language_code, "voice": voice, "audio_config": audio_config})
        yield self._tts_stream


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
    provider = FakeTTSProvider(FakeTTSStream(batches))

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
    provider = FakeTTSProvider(FakeTTSStream(batches))

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
    tts_stream = FakeTTSStream(batches)
    provider = FakeTTSProvider(tts_stream)

    try:
        with _connect(provider) as websocket:
            websocket.send_text("aap patr hain")
            websocket.close()
            time.sleep(0.1)
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert tts_stream.sent_texts == ["aap patr hain"]


def test_handles_multiple_replies_on_one_connection():
    batches = [
        [TTSStreamEvent(type=TTSEventType.AUDIO, raw={}, audio=b"reply-one"), TTSStreamEvent(type=TTSEventType.COMPLETE, raw={})],
        [TTSStreamEvent(type=TTSEventType.AUDIO, raw={}, audio=b"reply-two"), TTSStreamEvent(type=TTSEventType.COMPLETE, raw={})],
    ]
    tts_stream = FakeTTSStream(batches)
    provider = FakeTTSProvider(tts_stream)

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
    assert tts_stream.sent_texts == ["first reply", "second reply"]


def test_stops_relaying_on_error_event_without_hanging():
    batches = [
        [
            TTSStreamEvent(type=TTSEventType.AUDIO, raw={}, audio=b"partial"),
            TTSStreamEvent(type=TTSEventType.ERROR, raw={}, message="synthesis failed"),
        ]
    ]
    provider = FakeTTSProvider(FakeTTSStream(batches))

    try:
        with _connect(provider) as websocket:
            websocket.send_text("hello")
            partial = websocket.receive_bytes()
            websocket.close()
            time.sleep(0.1)
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert partial == b"partial"


def test_client_disconnect_tears_down_cleanly_mid_session():
    batches = [[TTSStreamEvent(type=TTSEventType.COMPLETE, raw={})]]
    tts_stream = FakeTTSStream(batches)
    provider = FakeTTSProvider(tts_stream)

    try:
        with _connect(provider) as websocket:
            websocket.close()
            time.sleep(0.1)
    finally:
        app.dependency_overrides.pop(get_tts_provider_ws, None)

    assert tts_stream.sent_texts == []