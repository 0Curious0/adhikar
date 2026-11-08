from sarvamai import AsyncSarvamAI
from sarvamai.core.api_error import ApiError

from .base import DecisionProvider, DecisionState
from .exceptions import NLUError, NLURequestError
from .models import ChoiceAnswer, DecisionQuestion


class SarvamPrismProvider(DecisionProvider):
    MODEL = "sarvam-prism"

    def __init__(self, api_key: str):
        self._client = AsyncSarvamAI(api_subscription_key=api_key)

    async def decide(self, state: DecisionState, questions: dict[str, DecisionQuestion]) -> dict[str, ChoiceAnswer]:
        try:
            response = await self._client.decisions.create(
                model=self.MODEL,
                state=state,
                questions={
                    question_id: {"type": "choice", "instructions": q.instructions, "criteria": q.criteria}
                    for question_id, q in questions.items()
                },
            )
        except ApiError as e:
            raise NLURequestError(str(e), request_id=_request_id(e), status_code=e.status_code) from e

        answers: dict[str, ChoiceAnswer] = {}
        for question_id, answer in response.answers.items():
            if answer.type != "choice":
                raise NLUError(f"question {question_id!r}: expected a choice answer, got {answer.type!r}")
            answers[question_id] = ChoiceAnswer(
                choice=answer.choice, confidence=answer.confidence, probabilities=answer.probabilities
            )
        return answers


def _request_id(error: ApiError) -> str | None:
    return error.body.get("request_id") if isinstance(error.body, dict) else None