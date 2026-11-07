import json
from unittest.mock import AsyncMock

from adhikar.tts.models import AudioConfig
from adhikar.tts.provider import TimbreTTSProvider, TimbreTTSStream


async def test_send_text_sends_full_synthesis_request():
    ws = AsyncMock()
    stream = TimbreTTSStream(
        ws,
        language_code="hi-IN",
        voice="Nalini",
        speed=1.0,
        audio_config=AudioConfig(),
    )

    await stream.send_text("नमस्ते, आप कैसे हैं?")

    ws.send.assert_awaited_once()
    sent = json.loads(ws.send.await_args.args[0])
    assert sent["text"] == "नमस्ते, आप कैसे हैं?"
    assert sent["voice"] == "Nalini"
    assert sent["model"] == TimbreTTSProvider.MODEL
    assert sent["language"] == "hi-IN"
    assert sent["speed"] == 1.0
    assert sent["audio_config"] == AudioConfig().model_dump()


async def test_send_text_uses_stored_speed_and_audio_config():
    ws = AsyncMock()
    audio_config = AudioConfig(sample_rate=24000, container="raw")
    stream = TimbreTTSStream(
        ws,
        language_code="en-IN",
        voice="Kaveri",
        speed="slow",
        audio_config=audio_config,
    )

    await stream.send_text("Hello")

    sent = json.loads(ws.send.await_args.args[0])
    assert sent["speed"] == "slow"
    assert sent["audio_config"]["sample_rate"] == 24000
    assert sent["audio_config"]["container"] == "raw"
