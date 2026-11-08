from ..schemes.models import EligibilityRule, RuleOperator, SchemeDocument
from .exceptions import FieldSpecError
from .models import FieldSpec, FieldType

_NUMERIC_OPERATORS = {
    RuleOperator.GREATER_THAN_OR_EQUAL,
    RuleOperator.LESS_THAN_OR_EQUAL,
    RuleOperator.LESS_THAN,
    RuleOperator.BETWEEN_INCLUSIVE,
}


def _field_type_for_rule(rule: EligibilityRule) -> tuple[FieldType, list[str] | None]:
    if rule.operator == RuleOperator.IN:
        assert isinstance(rule.value, list)
        return FieldType.ENUM, [str(v) for v in rule.value]
    if rule.operator in _NUMERIC_OPERATORS:
        return FieldType.NUMBER, None
    if rule.operator == RuleOperator.EQUALS:
        if isinstance(rule.value, bool):
            return FieldType.BOOLEAN, None
        if isinstance(rule.value, str):
            return FieldType.STRING, None
        if isinstance(rule.value, (int, float)):
            return FieldType.NUMBER, None
        raise FieldSpecError(f"rule {rule.rule_id!r}: unsupported equals value type {type(rule.value).__name__!r}")
    raise FieldSpecError(f"rule {rule.rule_id!r}: unhandled operator {rule.operator!r}")


def build_field_specs(schemes: dict[str, SchemeDocument]) -> dict[str, FieldSpec]:
    """Derive one `FieldSpec` per distinct `EligibilityRule.field` across every loaded scheme.

    The type comes from `operator`, not from the rule's specific `value` — a rule testing
    `state_residency equals "Rajasthan"` says nothing about the field's real-world domain, it's
    just the one target that scheme happens to check against. Only `in` rules declare a true
    enum, since the rule author has to spell out every acceptable value for `in` to make sense.

    Raises `FieldSpecError` if the same field name implies a different type, or a different
    enum, in two different schemes — that's a data inconsistency worth surfacing loudly rather
    than silently picking one.
    """
    specs: dict[str, FieldSpec] = {}

    for scheme in schemes.values():
        for rule in scheme.eligibility_rules:
            field_type, enum_values = _field_type_for_rule(rule)
            existing = specs.get(rule.field)

            if existing is None:
                specs[rule.field] = FieldSpec(field=rule.field, type=field_type, enum_values=enum_values)
                continue

            if existing.type != field_type:
                raise FieldSpecError(
                    f"field {rule.field!r} is {existing.type.value} in one scheme and "
                    f"{field_type.value} in another (rule {rule.rule_id!r})"
                )
            if existing.enum_values is not None and set(existing.enum_values) != set(enum_values or []):
                raise FieldSpecError(
                    f"field {rule.field!r} has conflicting enum values across schemes (rule {rule.rule_id!r})"
                )

    return specs
