import asyncio
import time
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from adhikar.api.app import app
from adhikar.api.routes import get_stt_provider_ws
from adhikar.stt.models import STTEventType, STTStreamEvent


class FakeSTTStream:
    def __init__(self, events: list[STTStreamEvent], ready_event: asyncio.Event | None = None):
        self.sent_frames: list[bytes] = []
        self._events = events
        self._ready_event = ready_event

    async def send_audio(self, frame: bytes) -> None:
        self.sent_frames.append(frame)
        if self._ready_event is not None:
            self._ready_event.set()

    async def events(self):
        if self._ready_event is not None:
            await self._ready_event.wait()
        for event in self._events:
            yield event

    async def update_settings(self, **settings: object) -> None:
        pass


class HangingSTTStream:
    """Never emits an event, so the only way the session ends is the client disconnecting."""

    def __init__(self):
        self.sent_frames: list[bytes] = []

    async def send_audio(self, frame: bytes) -> None:
        self.sent_frames.append(frame)

    async def events(self):
        await asyncio.sleep(3600)
        yield  # pragma: no cover


class FakeSTTProvider:
    def __init__(self, stt_stream):
        self._stt_stream = stt_stream
        self.language_codes: list[str] = []

    @asynccontextmanager
    async def stream(self, *, language_code: str, sample_rate: int = 16000, output_style=None):
        self.language_codes.append(language_code)
        yield self._stt_stream


def _connect(provider: FakeSTTProvider, language_code: str = "hi-IN"):
    app.dependency_overrides[get_stt_provider_ws] = lambda: provider
    client = TestClient(app)
    return client.websocket_connect(f"/stt/stream?language_code={language_code}")


def test_relays_transcript_events_to_client_as_json():
    events = [
        STTStreamEvent(type=STTEventType.SPEECH_START, raw={}),
        STTStreamEvent(type=STTEventType.TRANSCRIPT, raw={}, text="main patr hoon", segment_id="s1", segment_index=0),
    ]
    provider = FakeSTTProvider(FakeSTTStream(events))

    try:
        with _connect(provider) as websocket:
            first = websocket.receive_json()
            second = websocket.receive_json()
    finally:
        app.dependency_overrides.pop(get_stt_provider_ws, None)

    assert first == {"type": "speech_start", "text": None, "segment_id": None, "segment_index": None}
    assert second == {"type": "transcript", "text": "main patr hoon", "segment_id": "s1", "segment_index": 0}


def test_passes_language_code_from_query_param_to_provider():
    provider = FakeSTTProvider(FakeSTTStream([STTStreamEvent(type=STTEventType.CONNECTED, raw={})]))

    try:
        with _connect(provider, language_code="ta-IN") as websocket:
            websocket.receive_json()
    finally:
        app.dependency_overrides.pop(get_stt_provider_ws, None)

    assert provider.language_codes == ["ta-IN"]


def test_forwards_client_audio_frames_to_the_stt_session():
    ready_event = asyncio.Event()
    stt_stream = FakeSTTStream([STTStreamEvent(type=STTEventType.CONNECTED, raw={})], ready_event=ready_event)
    provider = FakeSTTProvider(stt_stream)

    try:
        with _connect(provider) as websocket:
            websocket.send_bytes(b"\x00" * 1024)
            websocket.receive_json()
    finally:
        app.dependency_overrides.pop(get_stt_provider_ws, None)

    assert stt_stream.sent_frames == [b"\x00" * 1024]


def test_client_disconnect_tears_down_cleanly_with_no_events():
    stt_stream = HangingSTTStream()
    provider = FakeSTTProvider(stt_stream)

    try:
        with _connect(provider) as websocket:
            websocket.send_bytes(b"\x00" * 1024)
            # Explicitly close and give the server's background loop a moment to process the
            # disconnect and tear itself down gracefully, before the test client's own `__exit__`
            # force-cancels the session regardless of whether the app has finished.
            websocket.close()
            time.sleep(0.1)
    finally:
        app.dependency_overrides.pop(get_stt_provider_ws, None)

    assert stt_stream.sent_frames == [b"\x00" * 1024]
