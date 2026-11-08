from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class Intent(str, Enum):
    GRIEVANCE = "grievance"
    SCHEME_QUERY = "scheme_query"
    UPDATE_INFO = "update_info"
    UNRELATED = "unrelated"


class DecisionQuestion(BaseModel):
    """A Sarvam Prism `choice`-type question — the only question type this app uses."""

    model_config = ConfigDict(frozen=True)

    instructions: str
    criteria: dict[str, str]
    """Maps each option id to a short description of what it means."""


class ChoiceAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    choice: str
    confidence: float
    probabilities: dict[str, float]


class FieldType(str, Enum):
    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"
    ENUM = "enum"


class FieldSpec(BaseModel):
    """Describes one user-profile fact for the entity-extraction request: its name and shape.

    Derived from the `operator` on a scheme's `EligibilityRule`, not from the rule's `value` —
    the rule's value is the one target the scheme happens to check against, not the field's
    real-world domain (e.g. a rule testing `state_residency equals "Rajasthan"` does not mean
    the field can only ever be "Rajasthan"). Only `in` rules declare a true enum, since the rule
    author has to spell out every acceptable value for that operator to make sense at all.
    """

    model_config = ConfigDict(frozen=True)

    field: str
    type: FieldType
    enum_values: list[str] | None = None
    description: str | None = None
    """Optional guidance for the reasoning model, surfaced as the JSON schema property's
    `description`. Scheme-derived fields rarely need this — the field name is usually
    self-explanatory. It matters for fields whose purpose isn't obvious from the name alone,
    like a meta-field for detecting a scheme-switch request."""

    @model_validator(mode="after")
    def _check_enum_values_match_type(self) -> "FieldSpec":
        if self.type == FieldType.ENUM and not self.enum_values:
            raise ValueError("enum field type requires non-empty enum_values")
        if self.type != FieldType.ENUM and self.enum_values is not None:
            raise ValueError(f"{self.type.value} field type must not set enum_values")
        return self