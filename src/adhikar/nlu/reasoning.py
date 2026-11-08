import json
from typing import Any

from sarvamai import AsyncSarvamAI
from sarvamai.core.api_error import ApiError

from .base import ReasoningProvider
from .exceptions import NLUError, NLURequestError
from .models import FieldSpec, FieldType

_FIELD_TYPE_TO_JSON_SCHEMA_TYPE = {
    FieldType.BOOLEAN: "boolean",
    FieldType.NUMBER: "number",
    FieldType.STRING: "string",
    FieldType.ENUM: "string",
}

_SYSTEM_PROMPT = """
You extract structured facts about a welfare-scheme applicant from one utterance, for an Indian
voice assistant. The applicant may speak in Hindi, Tamil, Telugu, or English — always output
field values in English regardless of which language the utterance was in.

Rules:
1. Only return a field if the utterance actually states or clearly, unambiguously implies it.
   Never guess, never infer a field from an unrelated statement, and never fill in a default
   when something is uncertain or simply not mentioned — omit it entirely.
2. Numbers: convert spoken numbers and Indian numbering (lakh, crore) to plain digits.
   "2 lakh rupees" -> 200000. "fifty thousand" -> 50000. "1.5 crore" -> 15000000.
3. Indian state names: use the full official English name, never an abbreviation or
   local-language name. "I live in UP" -> "Uttar Pradesh". "naanga Tamil Nadu la irukkom"
   (Tamil) -> "Tamil Nadu".
4. Marital status: use exactly one of "widowed", "divorced", "married", "single", "abandoned".
   "My husband passed away" -> "widowed". "Main kabhi shaadi nahi ki" (Hindi) -> "single".
5. A yes/no statement about a boolean fact maps directly to true/false.
   "Haan, mere paas BPL card hai" (Hindi, "yes, I have a BPL card") -> true.
   "No, I don't have that" -> false.
6. Respond with only the JSON object described by the schema — no extra commentary.

Examples:
- "I'm 45 and my husband died two years ago" -> {"age_years": 45, "marital_status": "widowed"}
- "Hum Rajasthan se hain, BPL family hain" (Hindi, "we're from Rajasthan, a BPL family") ->
  {"state_residency": "Rajasthan", "special_eligibility_category": "bpl_family"}
""".strip()


class Sarvam105BReasoningProvider(ReasoningProvider):
    MODEL = "sarvam-105b"

    def __init__(self, api_key: str):
        self._client = AsyncSarvamAI(api_subscription_key=api_key)

    async def extract(self, text: str, field_specs: dict[str, FieldSpec]) -> dict[str, Any]:
        try:
            response = await self._client.chat.completions(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "extracted_facts", "schema": _build_json_schema(field_specs)},
                },
            )
        except ApiError as e:
            raise NLURequestError(str(e), request_id=_request_id(e), status_code=e.status_code) from e

        content = response.choices[0].message.content
        if content is None:
            raise NLUError("reasoning model returned no content")

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise NLUError(f"reasoning model returned invalid JSON: {content!r}") from e


def _build_json_schema(field_specs: dict[str, FieldSpec]) -> dict[str, Any]:
    """No `required` list: every field is optional, since an omitted field means "not mentioned",
    not "false"/"zero" — see `ReasoningProvider.extract`'s contract."""
    properties = {}
    for name, spec in field_specs.items():
        prop: dict[str, Any] = {"type": _FIELD_TYPE_TO_JSON_SCHEMA_TYPE[spec.type]}
        if spec.type == FieldType.ENUM:
            prop["enum"] = spec.enum_values
        properties[name] = prop

    return {"type": "object", "properties": properties, "additionalProperties": False}


def _request_id(error: ApiError) -> str | None:
    return error.body.get("request_id") if isinstance(error.body, dict) else None