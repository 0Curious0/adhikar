from typing import Any

from adhikar.nlu.base import ReasoningProvider
from adhikar.nlu.entities import REQUESTED_SCHEME_FIELD, extract_entities
from adhikar.nlu.models import FieldSpec, FieldType


class FakeReasoningProvider(ReasoningProvider):
    def __init__(self, result: dict[str, Any]):
        self._result = result
        self.last_field_specs: dict[str, FieldSpec] | None = None

    async def extract(self, text: str, field_specs: dict[str, FieldSpec]) -> dict[str, Any]:
        self.last_field_specs = field_specs
        return self._result


async def test_extract_entities_splits_facts_from_requested_scheme():
    provider = FakeReasoningProvider({"age_years": 45, REQUESTED_SCHEME_FIELD: "pds"})

    result = await extract_entities(
        provider, "I'm 45, actually ask about PDS", {"age_years": FieldSpec(field="age_years", type=FieldType.NUMBER)}, ["pm_kisan", "pds"]
    )

    assert result.facts == {"age_years": 45}
    assert result.requested_scheme == "pds"


async def test_extract_entities_requested_scheme_defaults_to_none():
    provider = FakeReasoningProvider({"age_years": 45})

    result = await extract_entities(
        provider, "I'm 45", {"age_years": FieldSpec(field="age_years", type=FieldType.NUMBER)}, ["pm_kisan", "pds"]
    )

    assert result.facts == {"age_years": 45}
    assert result.requested_scheme is None


async def test_extract_entities_adds_requested_scheme_field_spec():
    provider = FakeReasoningProvider({})

    await extract_entities(provider, "hello", {"age_years": FieldSpec(field="age_years", type=FieldType.NUMBER)}, ["pm_kisan", "pds"])

    sent_specs = provider.last_field_specs
    assert "age_years" in sent_specs
    requested_scheme_spec = sent_specs[REQUESTED_SCHEME_FIELD]
    assert requested_scheme_spec.type == FieldType.ENUM
    assert requested_scheme_spec.enum_values == ["pm_kisan", "pds"]
    assert requested_scheme_spec.description is not None


async def test_extract_entities_does_not_mutate_input_field_specs():
    field_specs = {"age_years": FieldSpec(field="age_years", type=FieldType.NUMBER)}
    provider = FakeReasoningProvider({})

    await extract_entities(provider, "hello", field_specs, ["pm_kisan", "pds"])

    assert REQUESTED_SCHEME_FIELD not in field_specs
