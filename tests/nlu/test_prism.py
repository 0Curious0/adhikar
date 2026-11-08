import json

import httpx
import pytest
import respx

from adhikar.nlu.exceptions import NLUError, NLURequestError
from adhikar.nlu.models import DecisionQuestion
from adhikar.nlu.prism import SarvamPrismProvider

URL = "https://api.sarvam.ai/v2/systemone"


def _response(answers: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json={"model": "sarvam-prism", "answers": answers, "usage": {"input_tokens": 1, "output_tokens": 0}},
    )


@respx.mock
async def test_decide_returns_choice_answers():
    respx.post(URL).mock(
        return_value=_response(
            {
                "intent": {
                    "type": "choice",
                    "choice": "scheme_query",
                    "confidence": 0.82,
                    "probabilities": {
                        "scheme_query": 0.9,
                        "grievance": 0.05,
                        "update_info": 0.03,
                        "unrelated": 0.02,
                    },
                }
            }
        )
    )

    provider = SarvamPrismProvider(api_key="test-key")
    answers = await provider.decide(
        "Am I eligible for PM-KISAN?",
        {
            "intent": DecisionQuestion(
                instructions="classify intent",
                criteria={"scheme_query": "...", "grievance": "...", "update_info": "...", "unrelated": "..."},
            )
        },
    )

    assert answers["intent"].choice == "scheme_query"
    assert answers["intent"].confidence == 0.82
    assert answers["intent"].probabilities["scheme_query"] == 0.9


@respx.mock
async def test_decide_sends_model_state_and_question_shape():
    route = respx.post(URL).mock(
        return_value=_response({"q": {"type": "choice", "choice": "a", "confidence": 1.0, "probabilities": {"a": 1.0}}})
    )

    provider = SarvamPrismProvider(api_key="test-key")
    await provider.decide("state text", {"q": DecisionQuestion(instructions="pick", criteria={"a": "desc a"})})

    body = json.loads(route.calls.last.request.content)
    assert body["model"] == "sarvam-prism"
    assert body["state"] == "state text"
    assert body["questions"]["q"] == {"type": "choice", "instructions": "pick", "criteria": {"a": "desc a"}}


@respx.mock
async def test_decide_raises_nlu_request_error_on_api_error():
    respx.post(URL).mock(
        return_value=httpx.Response(400, json={"message": "bad request", "code": "invalid", "request_id": "req_1"})
    )

    provider = SarvamPrismProvider(api_key="test-key")

    with pytest.raises(NLURequestError) as exc_info:
        await provider.decide("x", {"q": DecisionQuestion(instructions="i", criteria={"a": "d"})})

    assert exc_info.value.status_code == 400
    assert exc_info.value.request_id == "req_1"


@respx.mock
async def test_decide_raises_nlu_error_on_unexpected_answer_type():
    respx.post(URL).mock(return_value=_response({"q": {"type": "noul", "noul": 0.9}}))

    provider = SarvamPrismProvider(api_key="test-key")

    with pytest.raises(NLUError):
        await provider.decide("x", {"q": DecisionQuestion(instructions="i", criteria={"a": "d"})})
