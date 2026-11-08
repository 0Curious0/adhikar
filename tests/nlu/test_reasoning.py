import json

import httpx
import pytest
import respx

from adhikar.nlu.exceptions import NLUError, NLURequestError
from adhikar.nlu.models import FieldSpec, FieldType
from adhikar.nlu.reasoning import Sarvam105BReasoningProvider

URL = "https://api.sarvam.ai/v1/chat/completions"


def _response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl_1",
            "object": "chat.completion",
            "created": 0,
            "model": "sarvam-105b",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        },
    )


@respx.mock
async def test_extract_returns_only_mentioned_fields():
    respx.post(URL).mock(return_value=_response(json.dumps({"age_years": 45})))

    provider = Sarvam105BReasoningProvider(api_key="test-key")
    facts = await provider.extract(
        "I'm 45 years old",
        {
            "age_years": FieldSpec(field="age_years", type=FieldType.NUMBER),
            "state_residency": FieldSpec(field="state_residency", type=FieldType.STRING),
        },
    )

    assert facts == {"age_years": 45}


@respx.mock
async def test_extract_sends_schema_with_no_required_fields():
    route = respx.post(URL).mock(return_value=_response(json.dumps({})))

    provider = Sarvam105BReasoningProvider(api_key="test-key")
    await provider.extract(
        "hello",
        {
            "nfsa_category": FieldSpec(field="nfsa_category", type=FieldType.ENUM, enum_values=["PHH", "AAY"]),
            "household_bpl_status": FieldSpec(field="household_bpl_status", type=FieldType.BOOLEAN),
        },
    )

    body = json.loads(route.calls.last.request.content)
    schema = body["response_format"]["json_schema"]["schema"]
    assert "required" not in schema
    assert schema["properties"]["nfsa_category"] == {"type": "string", "enum": ["PHH", "AAY"]}
    assert schema["properties"]["household_bpl_status"] == {"type": "boolean"}
    assert body["model"] == "sarvam-105b"


@respx.mock
async def test_extract_raises_nlu_request_error_on_api_error():
    respx.post(URL).mock(
        return_value=httpx.Response(400, json={"message": "bad request", "code": "invalid", "request_id": "req_1"})
    )

    provider = Sarvam105BReasoningProvider(api_key="test-key")

    with pytest.raises(NLURequestError) as exc_info:
        await provider.extract("hi", {"age_years": FieldSpec(field="age_years", type=FieldType.NUMBER)})

    assert exc_info.value.status_code == 400
    assert exc_info.value.request_id == "req_1"


@respx.mock
async def test_extract_raises_nlu_error_on_invalid_json_content():
    respx.post(URL).mock(return_value=_response("not valid json"))

    provider = Sarvam105BReasoningProvider(api_key="test-key")

    with pytest.raises(NLUError):
        await provider.extract("hi", {"age_years": FieldSpec(field="age_years", type=FieldType.NUMBER)})
