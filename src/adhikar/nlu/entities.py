from typing import Any

from pydantic import BaseModel, ConfigDict

from .base import ReasoningProvider
from .models import FieldSpec, FieldType

REQUESTED_SCHEME_FIELD = "requested_scheme"

_REQUESTED_SCHEME_DESCRIPTION = (
    "The scheme the user wants to switch to or ask about next, only if they explicitly asked "
    "to change the topic/scheme (e.g. 'actually ask about PM-KISAN instead'). Do not set this "
    "for a question about the scheme already being discussed."
)


class ExtractedEntities(BaseModel):
    model_config = ConfigDict(frozen=True)

    facts: dict[str, Any] = {}
    requested_scheme: str | None = None


async def extract_entities(
    provider: ReasoningProvider,
    transcript: str,
    field_specs: dict[str, FieldSpec],
    scheme_ids: list[str],
) -> ExtractedEntities:
    """Extract demographic/eligibility facts plus an optional scheme-switch request.

    `field_specs` should be `build_field_specs()`'s output (scheme-derived facts only); this
    adds one more field on top of it — `requested_scheme`, an enum over `scheme_ids` with its
    own explanatory `description` since (unlike e.g. `age_years`) its purpose isn't obvious
    from the name alone — so the result can be split cleanly: `facts` merges into the user
    profile via `merge_facts`, `requested_scheme` (if set) drives `pin_scheme` instead.
    """
    full_specs = {
        **field_specs,
        REQUESTED_SCHEME_FIELD: FieldSpec(
            field=REQUESTED_SCHEME_FIELD,
            type=FieldType.ENUM,
            enum_values=scheme_ids,
            description=_REQUESTED_SCHEME_DESCRIPTION,
        ),
    }

    raw = await provider.extract(transcript, full_specs)

    return ExtractedEntities(
        facts={k: v for k, v in raw.items() if k != REQUESTED_SCHEME_FIELD},
        requested_scheme=raw.get(REQUESTED_SCHEME_FIELD),
    )