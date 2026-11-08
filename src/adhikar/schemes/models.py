from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class Jurisdiction(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: str
    country: str
    state: str | None = None


class RuleOperator(str, Enum):
    EQUALS = "equals"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    LESS_THAN = "less_than"
    BETWEEN_INCLUSIVE = "between_inclusive"
    IN = "in"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    PARTIALLY_VERIFIED = "partially_verified"


RuleValue = bool | int | float | str | list[bool | int | float | str]


class EligibilityRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    field: str
    operator: RuleOperator
    value: RuleValue
    verification_status: VerificationStatus
    source_ids: list[str] = []
    note: str | None = None
    rule_group: str | None = None
    """Rules sharing a `rule_group` are OR'd (any one passing satisfies the group); a rule with
    no `rule_group` is AND'd against every other rule/group as before."""

    @model_validator(mode="after")
    def _check_value_shape(self) -> "EligibilityRule":
        if self.operator == RuleOperator.BETWEEN_INCLUSIVE:
            if not (isinstance(self.value, list) and len(self.value) == 2):
                raise ValueError("between_inclusive requires a 2-element [min, max] value")
        elif self.operator == RuleOperator.IN:
            if not isinstance(self.value, list):
                raise ValueError("in requires a list value")
        elif isinstance(self.value, list):
            raise ValueError(f"{self.operator.value} requires a scalar value, not a list")
        return self


class Source(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    title: str
    publisher: str
    url: str
    checked_on: date | None = None
    supports: str | list[str] | None = None


class GrievanceChannel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    name: str
    type: str
    verification_status: VerificationStatus


class Grievance(BaseModel):
    model_config = ConfigDict(frozen=True)

    channels: list[GrievanceChannel] = []
    instructions: str
    verification_status: VerificationStatus
    sources: list[str] = []


class SchemeDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    schema_version: str
    scheme_id: str
    jurisdiction: Jurisdiction
    eligibility_rules: list[EligibilityRule] = []
    sources: list[Source] = []

    name: dict[str, str]
    description: dict[str, str] = {}
    benefits: dict[str, Any] = {}
    additional_benefits: list[Any] = []
    required_information: list[str] = []
    required_documents: list[Any] = []
    application: dict[str, Any] = {}
    grievance: Grievance | None = None
    verification: dict[str, Any] = {}
    notes: list[str] = []

    @model_validator(mode="after")
    def _check_source_ids_resolve(self) -> "SchemeDocument":
        known_ids = {source.source_id for source in self.sources}
        for rule in self.eligibility_rules:
            missing = set(rule.source_ids) - known_ids
            if missing:
                raise ValueError(f"rule {rule.rule_id} references unknown source_ids: {sorted(missing)}")
        return self