from abc import ABC, abstractmethod
from typing import Any

from .models import ChoiceAnswer, DecisionQuestion, FieldSpec


DecisionState = str | dict[str, Any] | list[Any]


class DecisionProvider(ABC):
    @abstractmethod
    async def decide(self, state: DecisionState, questions: dict[str, DecisionQuestion]) -> dict[str, ChoiceAnswer]:
        """Score every option of every question against `state` in one request.

        `state` may be a plain string or a structured object/array — e.g. to give a question
        extra context (such as which scheme is currently pinned) alongside the raw utterance.
        """


class ReasoningProvider(ABC):
    @abstractmethod
    async def extract(self, text: str, field_specs: dict[str, FieldSpec]) -> dict[str, Any]:
        """Extract whichever of `field_specs` are mentioned in `text`.

        Returns only the fields actually found — an omitted field means "not mentioned", not
        "false"/"zero"/"unknown value".
        """