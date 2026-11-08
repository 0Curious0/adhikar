from adhikar.schemes.evaluator import EligibilityStatus, RuleState, evaluate
from adhikar.schemes.models import SchemeDocument

BASE_SCHEME = {
    "schema_version": "1.0.0",
    "scheme_id": "test-scheme",
    "jurisdiction": {"level": "central", "country": "IN"},
    "name": {"en": "Test Scheme"},
}


def _doc(eligibility_rules: list[dict]) -> SchemeDocument:
    return SchemeDocument.model_validate({**BASE_SCHEME, "eligibility_rules": eligibility_rules})


def test_eligible_when_all_rules_pass():
    doc = _doc(
        [
            {"rule_id": "R1", "field": "age_years", "operator": "greater_than_or_equal", "value": 40, "verification_status": "verified"},
            {"rule_id": "R2", "field": "household_bpl_status", "operator": "equals", "value": True, "verification_status": "verified"},
        ]
    )

    result = evaluate(doc, {"age_years": 45, "household_bpl_status": True})

    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.failed_groups == []
    assert result.missing_groups == []


def test_missing_fields_when_some_facts_absent():
    doc = _doc(
        [
            {"rule_id": "R1", "field": "age_years", "operator": "greater_than_or_equal", "value": 40, "verification_status": "verified"},
            {"rule_id": "R2", "field": "household_bpl_status", "operator": "equals", "value": True, "verification_status": "verified"},
        ]
    )

    result = evaluate(doc, {"age_years": 45})

    assert result.status == EligibilityStatus.MISSING_FIELDS
    assert [[(c.rule.field, c.state) for c in g] for g in result.missing_groups] == [
        [("household_bpl_status", RuleState.MISSING)]
    ]


def test_not_eligible_takes_priority_over_missing_fields():
    doc = _doc(
        [
            {"rule_id": "R1", "field": "age_years", "operator": "greater_than_or_equal", "value": 40, "verification_status": "verified"},
            {"rule_id": "R2", "field": "household_bpl_status", "operator": "equals", "value": True, "verification_status": "verified"},
        ]
    )

    result = evaluate(doc, {"age_years": 25})

    assert result.status == EligibilityStatus.NOT_ELIGIBLE
    assert [[r.rule_id for r in g] for g in result.failed_groups] == [["R1"]]
    assert result.missing_groups == []


def test_between_inclusive_operator():
    doc = _doc(
        [{"rule_id": "R1", "field": "age_years", "operator": "between_inclusive", "value": [40, 79], "verification_status": "verified"}]
    )

    assert evaluate(doc, {"age_years": 39}).status == EligibilityStatus.NOT_ELIGIBLE
    assert evaluate(doc, {"age_years": 40}).status == EligibilityStatus.ELIGIBLE
    assert evaluate(doc, {"age_years": 79}).status == EligibilityStatus.ELIGIBLE
    assert evaluate(doc, {"age_years": 80}).status == EligibilityStatus.NOT_ELIGIBLE


def test_in_operator():
    doc = _doc(
        [{"rule_id": "R1", "field": "nfsa_category", "operator": "in", "value": ["PHH", "AAY"], "verification_status": "verified"}]
    )

    assert evaluate(doc, {"nfsa_category": "AAY"}).status == EligibilityStatus.ELIGIBLE
    assert evaluate(doc, {"nfsa_category": "APL"}).status == EligibilityStatus.NOT_ELIGIBLE


def test_less_than_and_less_than_or_equal_operators():
    doc = _doc(
        [
            {"rule_id": "R1", "field": "a", "operator": "less_than", "value": 48000, "verification_status": "verified"},
            {"rule_id": "R2", "field": "b", "operator": "less_than_or_equal", "value": 200000, "verification_status": "verified"},
        ]
    )

    assert evaluate(doc, {"a": 47999, "b": 200000}).status == EligibilityStatus.ELIGIBLE
    assert evaluate(doc, {"a": 48000, "b": 200000}).status == EligibilityStatus.NOT_ELIGIBLE


def test_no_rules_is_eligible():
    doc = _doc([])

    assert evaluate(doc, {}).status == EligibilityStatus.ELIGIBLE


def _grouped_doc() -> SchemeDocument:
    return _doc(
        [
            {
                "rule_id": "R1",
                "field": "annual_income_inr",
                "operator": "less_than",
                "value": 48000,
                "verification_status": "verified",
                "rule_group": "FINANCIAL",
            },
            {
                "rule_id": "R2",
                "field": "special_eligibility_category",
                "operator": "in",
                "value": ["bpl_family", "antyodaya_family"],
                "verification_status": "verified",
                "rule_group": "FINANCIAL",
            },
        ]
    )


def test_grouped_rules_pass_if_either_side_passes():
    doc = _grouped_doc()

    # income fails, but category passes -> group passes
    result = evaluate(doc, {"annual_income_inr": 60000, "special_eligibility_category": "bpl_family"})
    assert result.status == EligibilityStatus.ELIGIBLE

    # income passes, category fails -> group still passes
    result = evaluate(doc, {"annual_income_inr": 10000, "special_eligibility_category": "none"})
    assert result.status == EligibilityStatus.ELIGIBLE


def test_grouped_rules_fail_only_if_both_sides_fail():
    doc = _grouped_doc()

    result = evaluate(doc, {"annual_income_inr": 60000, "special_eligibility_category": "none"})

    assert result.status == EligibilityStatus.NOT_ELIGIBLE
    assert len(result.failed_groups) == 1
    assert {r.rule_id for r in result.failed_groups[0]} == {"R1", "R2"}


def test_grouped_rules_missing_if_undetermined_and_not_already_passing():
    doc = _grouped_doc()

    # category unknown, income fails on its own -> can't rule out category passing yet;
    # the whole group (including the already-failed sibling) comes back, each tagged with
    # its own state, so a consumer knows R2 is the one actually worth asking about
    result = evaluate(doc, {"annual_income_inr": 60000})
    assert result.status == EligibilityStatus.MISSING_FIELDS
    assert len(result.missing_groups) == 1
    assert {c.rule.rule_id: c.state for c in result.missing_groups[0]} == {
        "R1": RuleState.FAIL,
        "R2": RuleState.MISSING,
    }

    # both unknown -> same single group, both rules tagged MISSING
    result = evaluate(doc, {})
    assert result.status == EligibilityStatus.MISSING_FIELDS
    assert len(result.missing_groups) == 1
    assert {c.rule.rule_id: c.state for c in result.missing_groups[0]} == {
        "R1": RuleState.MISSING,
        "R2": RuleState.MISSING,
    }
