from typing import Any

from adhikar.nlu.base import ReasoningProvider
from adhikar.nlu.entities import extract_entities
from adhikar.nlu.models import FieldSpec, FieldType


class FakeReasoningProvider(ReasoningProvider):
    def __init__(self, result: dict[str, Any]):
        self._result = result
        self.last_field_specs: dict[str, FieldSpec] | None = None
        self.last_context: str | None = None

    async def extract(self, text: str, field_specs: dict[str, FieldSpec], *, context: str | None = None) -> dict[str, Any]:
        self.last_field_specs = field_specs
        self.last_context = context
        return self._result


async def test_extract_entities_returns_providers_facts():
    provider = FakeReasoningProvider({"age_years": 45})

    result = await extract_entities(
        provider, "I'm 45", {"age_years": FieldSpec(field="age_years", type=FieldType.NUMBER)}
    )

    assert result == {"age_years": 45}


async def test_extract_entities_passes_field_specs_through_unchanged():
    field_specs = {"age_years": FieldSpec(field="age_years", type=FieldType.NUMBER)}
    provider = FakeReasoningProvider({})

    await extract_entities(provider, "hello", field_specs)

    assert provider.last_field_specs is field_specs


async def test_extract_entities_passes_context_through():
    provider = FakeReasoningProvider({})

    await extract_entities(
        provider,
        "yes, we do",
        {"family_owns_cultivable_land": FieldSpec(field="family_owns_cultivable_land", type=FieldType.BOOLEAN)},
        context="family_owns_cultivable_land",
    )

    assert provider.last_context == "family_owns_cultivable_land"
