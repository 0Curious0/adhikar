import pytest
from pydantic import ValidationError

from adhikar.schemes.models import EligibilityRule, SchemeDocument

BASE_SCHEME = {
    "schema_version": "1.0.0",
    "scheme_id": "test-scheme",
    "jurisdiction": {"level": "central", "country": "IN"},
    "name": {"en": "Test Scheme"},
}


def _rule(**overrides) -> dict:
    rule = {
        "rule_id": "R1",
        "field": "age_years",
        "operator": "equals",
        "value": True,
        "verification_status": "verified",
    }
    rule.update(overrides)
    return rule


def test_between_inclusive_accepts_two_element_list():
    rule = EligibilityRule.model_validate(_rule(operator="between_inclusive", value=[40, 79]))
    assert rule.value == [40, 79]


def test_between_inclusive_rejects_scalar_value():
    with pytest.raises(ValidationError):
        EligibilityRule.model_validate(_rule(operator="between_inclusive", value=40))


def test_in_accepts_list_value():
    rule = EligibilityRule.model_validate(_rule(operator="in", value=["widowed", "divorced"]))
    assert rule.value == ["widowed", "divorced"]


def test_in_rejects_scalar_value():
    with pytest.raises(ValidationError):
        EligibilityRule.model_validate(_rule(operator="in", value="widowed"))


def test_equals_accepts_scalar_value():
    rule = EligibilityRule.model_validate(_rule(operator="equals", value=False))
    assert rule.value is False


def test_equals_rejects_list_value():
    with pytest.raises(ValidationError):
        EligibilityRule.model_validate(_rule(operator="equals", value=[True, False]))


def test_scheme_document_accepts_rule_with_resolvable_source_id():
    doc = SchemeDocument.model_validate(
        {
            **BASE_SCHEME,
            "sources": [{"source_id": "SRC-1", "title": "T", "publisher": "P", "url": "https://example.com"}],
            "eligibility_rules": [_rule(source_ids=["SRC-1"])],
        }
    )
    assert doc.eligibility_rules[0].source_ids == ["SRC-1"]


def test_scheme_document_rejects_rule_with_unknown_source_id():
    with pytest.raises(ValidationError):
        SchemeDocument.model_validate(
            {
                **BASE_SCHEME,
                "sources": [],
                "eligibility_rules": [_rule(source_ids=["SRC-MISSING"])],
            }
        )
