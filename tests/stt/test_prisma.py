import httpx
import pytest
import respx

from adhikar.stt.exceptions import STTRequestError
from adhikar.stt.prisma import PrismaSTTProvider


@respx.mock
async def test_transcribe_success():
    route = respx.post("https://api.vachana.ai/stt/v3").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "request_id": "req_abc123",
                "transcript": "नमस्ते, आप कैसे हैं?",
                "model": "gnani-prisma-v2.5",
                "processing_time": 0.14,
                "end_to_end_latency": 0.17,
                "output": {"literal": "नमस्ते, आप कैसे हैं?"},
            },
        )
    )

    provider = PrismaSTTProvider(api_key="test-key")
    result = await provider.transcribe(b"fake-audio-bytes", language_code="hi-IN")
    await provider.aclose()

    assert result.transcript == "नमस्ते, आप कैसे हैं?"
    assert result.literal == "नमस्ते, आप कैसे हैं?"
    assert result.language_code == "hi-IN"
    assert result.request_id == "req_abc123"
    assert result.truncated is False

    sent_request = route.calls.last.request
    assert sent_request.headers["X-API-Key-ID"] == "test-key"
    assert b'name="language_code"' in sent_request.content
    assert b"hi-IN" in sent_request.content
    assert b'name="format"' in sent_request.content
    assert b"verbatim" in sent_request.content


@respx.mock
async def test_transcribe_failure_raises_stt_request_error():
    respx.post("https://api.vachana.ai/stt/v3").mock(
        return_value=httpx.Response(
            400,
            json={
                "success": False,
                "request_id": "req_def456",
                "error": {"message": "Unsupported language code"},
            },
        )
    )

    provider = PrismaSTTProvider(api_key="test-key")

    with pytest.raises(STTRequestError) as exc_info:
        await provider.transcribe(b"fake-audio-bytes", language_code="xx-XX")
    await provider.aclose()

    assert str(exc_info.value) == "Unsupported language code"
    assert exc_info.value.request_id == "req_def456"
    assert exc_info.value.status_code == 400
