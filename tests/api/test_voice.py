from httpx import ASGITransport, AsyncClient

from adhikar.api.app import app
from adhikar.api.routes import get_orchestrator, get_stt_provider, get_tts_provider
from adhikar.stt import TranscriptResult


class FakeOrchestrator:
    def __init__(self, reply: str | None):
        self._reply = reply
        self.calls: list[dict[str, str]] = []

    async def handle_turn(self, *, user_id: str, transcript: str, language_code: str) -> str | None:
        self.calls.append({"user_id": user_id, "transcript": transcript, "language_code": language_code})
        return self._reply


class RaisingOrchestrator:
    async def handle_turn(self, *, user_id: str, transcript: str, language_code: str) -> str | None:
        raise RuntimeError("boom")


class RaisingSTTProvider:
    async def transcribe(self, audio: bytes, *, language_code: str, output_style=None, filename="audio.wav"):
        raise RuntimeError("boom")


class RaisingTTSProvider:
    async def synthesize(self, text: str, *, language_code: str, voice: str, speed=1.0, audio_config=None) -> bytes:
        raise RuntimeError("boom")


class FakeSTTProvider:
    def __init__(self, transcript: str):
        self._transcript = transcript
        self.calls: list[dict[str, str]] = []

    async def transcribe(self, audio: bytes, *, language_code: str, output_style=None, filename="audio.wav"):
        self.calls.append({"audio": audio, "language_code": language_code, "filename": filename})
        return TranscriptResult(
            transcript=self._transcript, literal=self._transcript, language_code=language_code, request_id="r1"
        )


class FakeTTSProvider:
    def __init__(self):
        self.calls: list[dict[str, str]] = []

    async def synthesize(self, text: str, *, language_code: str, voice: str, speed=1.0, audio_config=None) -> bytes:
        self.calls.append({"text": text, "language_code": language_code, "voice": voice})
        return f"AUDIO[{text}]".encode()


async def _post_voice(orchestrator, stt_provider, tts_provider, *, audio: bytes = b"raw-audio-bytes"):
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_stt_provider] = lambda: stt_provider
    app.dependency_overrides[get_tts_provider] = lambda: tts_provider
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/voice",
                data={"user_id": "u1", "language_code": "hi-IN"},
                files={"audio": ("clip.wav", audio, "audio/wav")},
            )
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_stt_provider, None)
        app.dependency_overrides.pop(get_tts_provider, None)


async def test_voice_transcribes_runs_orchestrator_and_synthesizes_reply():
    orchestrator = FakeOrchestrator(reply="aap patr hain")
    stt = FakeSTTProvider(transcript="kya main patr hoon")
    tts = FakeTTSProvider()

    response = await _post_voice(orchestrator, stt, tts)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"AUDIO[aap patr hain]"


async def test_voice_passes_audio_bytes_and_language_code_to_stt():
    orchestrator = FakeOrchestrator(reply="ok")
    stt = FakeSTTProvider(transcript="whatever")
    tts = FakeTTSProvider()

    await _post_voice(orchestrator, stt, tts, audio=b"the-actual-bytes")

    assert stt.calls[0]["audio"] == b"the-actual-bytes"
    assert stt.calls[0]["language_code"] == "hi-IN"


async def test_voice_passes_stt_transcript_and_language_code_to_orchestrator():
    orchestrator = FakeOrchestrator(reply="ok")
    stt = FakeSTTProvider(transcript="kya main patr hoon")
    tts = FakeTTSProvider()

    await _post_voice(orchestrator, stt, tts)

    assert orchestrator.calls == [{"user_id": "u1", "transcript": "kya main patr hoon", "language_code": "hi-IN"}]


async def test_voice_uses_default_voice_for_synthesis():
    orchestrator = FakeOrchestrator(reply="aap patr hain")
    stt = FakeSTTProvider(transcript="whatever")
    tts = FakeTTSProvider()

    await _post_voice(orchestrator, stt, tts)

    assert tts.calls == [{"text": "aap patr hain", "language_code": "hi-IN", "voice": "Nalini"}]


async def test_voice_returns_no_content_when_orchestrator_has_nothing_to_say():
    orchestrator = FakeOrchestrator(reply=None)
    stt = FakeSTTProvider(transcript="lol random")
    tts = FakeTTSProvider()

    response = await _post_voice(orchestrator, stt, tts)

    assert response.status_code == 204
    assert response.content == b""
    assert tts.calls == []


async def test_voice_synthesizes_fallback_reply_when_orchestrator_raises():
    orchestrator = RaisingOrchestrator()
    stt = FakeSTTProvider(transcript="kya main patr hoon")
    tts = FakeTTSProvider()

    response = await _post_voice(orchestrator, stt, tts)

    assert response.status_code == 200
    assert tts.calls[0]["text"] == "क्षमा करें, कुछ गड़बड़ी हुई। कृपया फिर से कोशिश करें।"


async def test_voice_synthesizes_fallback_reply_when_stt_raises():
    orchestrator = FakeOrchestrator(reply="unreachable")
    stt = RaisingSTTProvider()
    tts = FakeTTSProvider()

    response = await _post_voice(orchestrator, stt, tts)

    assert response.status_code == 200
    assert tts.calls[0]["text"] == "क्षमा करें, कुछ गड़बड़ी हुई। कृपया फिर से कोशिश करें।"
    assert orchestrator.calls == []


async def test_voice_returns_no_content_when_even_fallback_synthesis_fails():
    orchestrator = RaisingOrchestrator()
    stt = FakeSTTProvider(transcript="kya main patr hoon")
    tts = RaisingTTSProvider()

    response = await _post_voice(orchestrator, stt, tts)

    assert response.status_code == 204
    assert response.content == b""
