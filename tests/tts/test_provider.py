import json

import httpx
import pytest
import respx

from adhikar.tts.exceptions import TTSRequestError
from adhikar.tts.provider import TimbreTTSProvider


@respx.mock
async def test_synthesize_success():
    audio_bytes = b"RIFF-fake-wav-bytes"
    route = respx.post("https://api.vachana.ai/api/v1/tts/inference").mock(
        return_value=httpx.Response(200, content=audio_bytes)
    )

    provider = TimbreTTSProvider(api_key="test-key")
    result = await provider.synthesize("नमस्ते, आप कैसे हैं?", language_code="hi-IN", voice="Nalini")
    await provider.aclose()

    assert result == audio_bytes

    sent_request = route.calls.last.request
    assert sent_request.headers["X-API-Key-ID"] == "test-key"
    body = json.loads(sent_request.content)
    assert body["text"] == "नमस्ते, आप कैसे हैं?"
    assert body["voice"] == "Nalini"
    assert body["model"] == TimbreTTSProvider.MODEL
    assert body["language"] == "hi-IN"
    assert body["speed"] == 1.0
    assert body["audio_config"]["container"] == "wav"


@respx.mock
async def test_synthesize_failure_flat_shape_raises_tts_request_error():
    respx.post("https://api.vachana.ai/api/v1/tts/inference").mock(
        return_value=httpx.Response(
            400,
            json={
                "success": False,
                "message": "Invalid request: Field required at body -> text",
                "status_code": 400,
            },
        )
    )

    provider = TimbreTTSProvider(api_key="test-key")

    with pytest.raises(TTSRequestError) as exc_info:
        await provider.synthesize("", language_code="hi-IN", voice="Nalini")
    await provider.aclose()

    assert str(exc_info.value) == "Invalid request: Field required at body -> text"
    assert exc_info.value.status_code == 400


@respx.mock
async def test_synthesize_failure_detail_shape_raises_tts_request_error():
    respx.post("https://api.vachana.ai/api/v1/tts/inference").mock(
        return_value=httpx.Response(
            401,
            json={
                "detail": {
                    "error_code": "INVALID_API_KEY",
                    "message": "Unauthorized",
                    "status_code": 401,
                }
            },
        )
    )

    provider = TimbreTTSProvider(api_key="bad-key")

    with pytest.raises(TTSRequestError) as exc_info:
        await provider.synthesize("नमस्ते", language_code="hi-IN", voice="Nalini")
    await provider.aclose()

    assert str(exc_info.value) == "Unauthorized"
    assert exc_info.value.status_code == 401
