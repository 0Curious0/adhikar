import pytest

from adhikar.nlu.exceptions import FieldSpecError
from adhikar.nlu.field_specs import build_field_specs
from adhikar.nlu.models import FieldType
from adhikar.schemes.models import SchemeDocument

BASE_SCHEME = {
    "schema_version": "1.0.0",
    "jurisdiction": {"level": "central", "country": "IN"},
    "name": {"en": "Test Scheme"},
}


def _scheme(scheme_id: str, eligibility_rules: list[dict]) -> SchemeDocument:
    return SchemeDocument.model_validate({**BASE_SCHEME, "scheme_id": scheme_id, "eligibility_rules": eligibility_rules})


def _rule(**overrides) -> dict:
    rule = {"rule_id": "R1", "field": "f", "operator": "equals", "value": True, "verification_status": "verified"}
    rule.update(overrides)
    return rule


def test_derives_boolean_from_equals_bool():
    schemes = {"a": _scheme("a", [_rule(field="household_bpl_status", operator="equals", value=True)])}

    specs = build_field_specs(schemes)

    assert specs["household_bpl_status"].type == FieldType.BOOLEAN
    assert specs["household_bpl_status"].enum_values is None


def test_derives_string_from_equals_string():
    schemes = {"a": _scheme("a", [_rule(field="state_residency", operator="equals", value="Rajasthan")])}

    specs = build_field_specs(schemes)

    assert specs["state_residency"].type == FieldType.STRING
    assert specs["state_residency"].enum_values is None


def test_derives_number_from_equals_number():
    schemes = {"a": _scheme("a", [_rule(field="age_years", operator="equals", value=18)])}

    specs = build_field_specs(schemes)

    assert specs["age_years"].type == FieldType.NUMBER


@pytest.mark.parametrize("operator", ["greater_than_or_equal", "less_than_or_equal", "less_than"])
def test_derives_number_from_comparison_operators(operator):
    schemes = {"a": _scheme("a", [_rule(field="age_years", operator=operator, value=40)])}

    specs = build_field_specs(schemes)

    assert specs["age_years"].type == FieldType.NUMBER


def test_derives_number_from_between_inclusive():
    schemes = {"a": _scheme("a", [_rule(field="age_years", operator="between_inclusive", value=[40, 79])])}

    specs = build_field_specs(schemes)

    assert specs["age_years"].type == FieldType.NUMBER


def test_derives_enum_from_in_operator():
    schemes = {"a": _scheme("a", [_rule(field="nfsa_category", operator="in", value=["PHH", "AAY"])])}

    specs = build_field_specs(schemes)

    assert specs["nfsa_category"].type == FieldType.ENUM
    assert specs["nfsa_category"].enum_values == ["PHH", "AAY"]


def test_same_field_consistent_across_schemes_is_not_a_conflict():
    schemes = {
        "a": _scheme("a", [_rule(field="age_years", operator="greater_than_or_equal", value=18)]),
        "b": _scheme("b", [_rule(field="age_years", operator="between_inclusive", value=[40, 79])]),
    }

    specs = build_field_specs(schemes)

    assert specs["age_years"].type == FieldType.NUMBER


def test_same_field_different_equals_value_is_not_a_conflict():
    # state_residency equals "Rajasthan" in one file and "Uttar Pradesh" in another: same type
    # (string), different target value per scheme — that's fine, not a type conflict.
    schemes = {
        "a": _scheme("a", [_rule(field="state_residency", operator="equals", value="Rajasthan")]),
        "b": _scheme("b", [_rule(field="state_residency", operator="equals", value="Uttar Pradesh")]),
    }

    specs = build_field_specs(schemes)

    assert specs["state_residency"].type == FieldType.STRING


def test_conflicting_type_across_schemes_raises():
    schemes = {
        "a": _scheme("a", [_rule(field="x", operator="equals", value=True)]),
        "b": _scheme("b", [_rule(field="x", operator="greater_than_or_equal", value=10)]),
    }

    with pytest.raises(FieldSpecError):
        build_field_specs(schemes)


def test_conflicting_enum_values_across_schemes_raises():
    schemes = {
        "a": _scheme("a", [_rule(field="category", operator="in", value=["a", "b"])]),
        "b": _scheme("b", [_rule(field="category", operator="in", value=["c", "d"])]),
    }

    with pytest.raises(FieldSpecError):
        build_field_specs(schemes)


def test_no_eligibility_rules_is_empty():
    schemes = {"a": _scheme("a", [])}

    assert build_field_specs(schemes) == {}