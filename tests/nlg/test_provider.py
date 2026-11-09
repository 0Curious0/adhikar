import json

import httpx
import pytest
import respx

from adhikar.nlg.exceptions import NLGError, NLGRequestError
from adhikar.nlg.provider import Sarvam105BConversationsProvider

URL = "https://api.sarvam.ai/v1/chat/completions"


def _response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl_1",
            "object": "chat.completion",
            "created": 0,
            "model": "sarvam-105b-conversations",
            "choices": [
                {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}
            ],
        },
    )


@respx.mock
async def test_reply_returns_model_content():
    respx.post(URL).mock(return_value=_response("आप पीएम-किसान के लिए पात्र हैं।"))

    provider = Sarvam105BConversationsProvider(api_key="test-key")
    reply = await provider.reply(
        system_prompt="Tell the user they're eligible for PM-KISAN.",
        user_message="eligible, benefit 6000 INR/year",
        language_code="hi-IN",
    )

    assert reply == "आप पीएम-किसान के लिए पात्र हैं।"


@respx.mock
async def test_reply_sends_model_and_messages():
    route = respx.post(URL).mock(return_value=_response("ok"))

    provider = Sarvam105BConversationsProvider(api_key="test-key")
    await provider.reply(system_prompt="Ask for age.", user_message="missing: age_years", language_code="ta-IN")

    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "sarvam-105b-conversations"
    assert body["messages"][1] == {"role": "user", "content": "missing: age_years"}
    assert "Ask for age." in body["messages"][0]["content"]
    assert "Tamil" in body["messages"][0]["content"]


@respx.mock
async def test_reply_accepts_each_of_the_10_mvp_languages():
    route = respx.post(URL).mock(return_value=_response("ok"))
    provider = Sarvam105BConversationsProvider(api_key="test-key")

    for language_code, language_name in [
        ("hi-IN", "Hindi"),
        ("en-IN", "English"),
        ("bn-IN", "Bengali"),
        ("gu-IN", "Gujarati"),
        ("kn-IN", "Kannada"),
        ("ml-IN", "Malayalam"),
        ("mr-IN", "Marathi"),
        ("pa-IN", "Punjabi"),
        ("ta-IN", "Tamil"),
        ("te-IN", "Telugu"),
    ]:
        await provider.reply(system_prompt="x", user_message="y", language_code=language_code)
        body = json.loads(route.calls.last.request.content)
        assert language_name in body["messages"][0]["content"]


async def test_reply_raises_nlg_error_on_unsupported_language():
    provider = Sarvam105BConversationsProvider(api_key="test-key")

    with pytest.raises(NLGError):
        await provider.reply(system_prompt="x", user_message="y", language_code="fr-FR")


@respx.mock
async def test_reply_raises_nlg_request_error_on_api_error():
    respx.post(URL).mock(
        return_value=httpx.Response(400, json={"message": "bad request", "code": "invalid", "request_id": "req_1"})
    )

    provider = Sarvam105BConversationsProvider(api_key="test-key")

    with pytest.raises(NLGRequestError) as exc_info:
        await provider.reply(system_prompt="x", user_message="y", language_code="en-IN")

    assert exc_info.value.status_code == 400
    assert exc_info.value.request_id == "req_1"


@respx.mock
async def test_reply_raises_nlg_error_on_no_content():
    respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "chatcmpl_1",
                "object": "chat.completion",
                "created": 0,
                "model": "sarvam-105b-conversations",
                "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": None}}],
            },
        )
    )

    provider = Sarvam105BConversationsProvider(api_key="test-key")

    with pytest.raises(NLGError):
        await provider.reply(system_prompt="x", user_message="y", language_code="en-IN")