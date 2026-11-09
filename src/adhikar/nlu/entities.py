from typing import Any

from .base import ReasoningProvider
from .models import FieldSpec


async def extract_entities(
    provider: ReasoningProvider,
    transcript: str,
    field_specs: dict[str, FieldSpec],
    *,
    context: str | None = None,
) -> dict[str, Any]:
    """Extract demographic/eligibility facts mentioned in `transcript`.

    `field_specs` should be `build_field_specs()`'s output, scoped to whichever scheme is
    actually relevant to this turn — not necessarily every loaded scheme's fields combined (see
    `Orchestrator._field_specs_by_scheme`). Scheme-switch detection is a separate, fixed-choice
    decision handled by `intent.classify_requested_scheme` via Prism, not by this function:
    folding it into this same JSON-schema extraction call was tried first and made both parts
    less reliable — it missed real scheme switches and fabricated unrelated facts (default-
    looking values the transcript never stated) on the same exact input across repeated calls.

    `context` (optional): comma-joined field names the assistant's last reply actually asked
    about (see `Orchestrator._build_eligibility_message`'s asked-fields bookkeeping), passed
    straight through to `provider.extract`.
    """
    return await provider.extract(transcript, field_specs, context=context)
