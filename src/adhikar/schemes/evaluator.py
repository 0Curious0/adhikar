from collections import defaultdict
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

from .models import EligibilityRule, RuleOperator, SchemeDocument


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    MISSING_FIELDS = "missing_fields"


class RuleState(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    MISSING = "missing"


class RuleCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule: EligibilityRule
    state: RuleState
    """Never PASS here: a group only ends up in `missing_groups` once we know no rule in it has
    already passed, so every member is either FAIL (checked, didn't satisfy it) or MISSING
    (field not in facts yet — this is the one worth asking about)."""


class EligibilityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: EligibilityStatus
    failed_groups: list[list[EligibilityRule]] = []
    """Each entry is one fully-failed rule group: every alternative in the group was checked and
    none passed. A singleton (ungrouped) rule that failed is its own one-rule group here."""
    missing_groups: list[list[RuleCheck]] = []
    """Each entry is one not-yet-decided rule group, with every one of its rules tagged FAIL or
    MISSING — so a consumer can tell which rule(s) are actually worth asking about (MISSING)
    versus an already-checked alternative sibling (FAIL) kept for context."""


def _rule_passes(rule: EligibilityRule, value: Any) -> bool:
    if rule.operator == RuleOperator.EQUALS:
        return value == rule.value
    if rule.operator == RuleOperator.GREATER_THAN_OR_EQUAL:
        return value >= rule.value
    if rule.operator == RuleOperator.LESS_THAN_OR_EQUAL:
        return value <= rule.value
    if rule.operator == RuleOperator.LESS_THAN:
        return value < rule.value
    if rule.operator == RuleOperator.BETWEEN_INCLUSIVE:
        low, high = rule.value
        return low <= value <= high
    if rule.operator == RuleOperator.IN:
        return value in rule.value
    raise ValueError(f"unhandled operator: {rule.operator}")


def _rule_state(rule: EligibilityRule, facts: dict[str, Any]) -> RuleState:
    if rule.field not in facts:
        return RuleState.MISSING
    return RuleState.PASS if _rule_passes(rule, facts[rule.field]) else RuleState.FAIL


def _group_key(rule: EligibilityRule) -> str:
    return rule.rule_group if rule.rule_group is not None else rule.rule_id


def evaluate(doc: SchemeDocument, facts: dict[str, Any]) -> EligibilityResult:
    """AND every eligibility-rule group in `doc` against `facts` (keyed by `EligibilityRule.field`).

    Rules sharing a `rule_group` are OR'd together first (any one passing satisfies the group);
    a rule with no `rule_group` is its own singleton group, AND'd against every other group. A
    known failure always takes priority over missing fields: if we already know the user is
    disqualified, there is no need to keep asking for more information.
    """
    groups: dict[str, list[EligibilityRule]] = defaultdict(list)
    for rule in doc.eligibility_rules:
        groups[_group_key(rule)].append(rule)

    failed_groups: list[list[EligibilityRule]] = []
    missing_groups: list[list[RuleCheck]] = []

    for rules in groups.values():
        checks = [RuleCheck(rule=rule, state=_rule_state(rule, facts)) for rule in rules]
        states = [check.state for check in checks]

        if RuleState.PASS in states:
            continue
        if RuleState.MISSING in states:
            missing_groups.append(checks)
            continue
        failed_groups.append(rules)

    if failed_groups:
        return EligibilityResult(status=EligibilityStatus.NOT_ELIGIBLE, failed_groups=failed_groups)
    if missing_groups:
        return EligibilityResult(status=EligibilityStatus.MISSING_FIELDS, missing_groups=missing_groups)
    return EligibilityResult(status=EligibilityStatus.ELIGIBLE)
