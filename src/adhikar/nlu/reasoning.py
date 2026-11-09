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
voice assistant. The applicant may speak in Hindi, English, Bengali, Gujarati, Kannada,
Malayalam, Marathi, Punjabi, Tamil, or Telugu — always output field values in English regardless
of which language the utterance was in.

Rules:
1. Only return a field if the utterance actually states or clearly, unambiguously implies it.
   Never guess, never infer a field from an unrelated statement, and never fill in a default
   when something is uncertain or simply not mentioned — omit it entirely.
2. Numbers: convert spoken numbers and Indian numbering (lakh, crore) to plain digits.
   "2 lakh rupees" -> 200000. "fifty thousand" -> 50000. "1.5 crore" -> 15000000.
3. Indian state names: use the full official English name, never an abbreviation or
   local-language name. "I live in UP" -> "Uttar Pradesh". "naanga Tamil Nadu la irukkom"
   (Tamil) -> "Tamil Nadu". "Ami Paschimbanga theke" (Bengali, "I'm from West Bengal") ->
   "West Bengal".
4. Marital status: use exactly one of "widowed", "divorced", "married", "single", "abandoned".
   "My husband passed away" -> "widowed". "Main kabhi shaadi nahi ki" (Hindi) -> "single".
   "Majhe lagna zhale nahi" (Marathi, "I never got married") -> "single".
5. A yes/no statement about a boolean fact maps directly to true/false — on its own, "yes"/"no"
   doesn't say which field, so find the subject noun the utterance is actually affirming or
   denying (pension, BPL card, ration card, government job, etc.) and match it to whichever
   boolean field's name refers to that same real-world thing, even if that exact field wasn't the
   one just asked about and even if the utterance never names the field, only the subject.
   "Haan, mere paas BPL card hai" (Hindi, "yes, I have a BPL card") -> household_bpl_status: true.
   "No, I don't get any other pension" -> receives_other_government_pension: false.
   "Nahi, mujhe koi sarkari naukri nahi hai" (Hindi, "no, I don't have any government job") ->
   applicant_or_son_government_employee_or_pensioner: false.
   If no field's name corresponds to the subject the utterance names, omit it — don't attach the
   true/false to an unrelated boolean field just because one exists in the schema.
6. Respond with only the JSON object described by the schema — no extra commentary.
7. The user message may start with a line "The assistant just asked about: <fields>" before the
   actual reply. Use that only to figure out *which* field a short, vague, or otherwise
   ambiguous reply is answering — e.g. if told the assistant just asked about
   `family_owns_cultivable_land_as_per_state_land_records`, a reply of "yes, we do" clearly
   answers that field even though it never names it. This never changes what rule 1 requires:
   still extract only what the reply *itself* actually states — the asked-about fields are a
   hint for attribution, not a license to fill them in regardless of what was said.

Examples:
- "I'm 45 and my husband died two years ago" -> {"age_years": 45, "marital_status": "widowed"}
- "Hum Rajasthan se hain, BPL family hain" (Hindi, "we're from Rajasthan, a BPL family") ->
  {"state_residency": "Rajasthan", "special_eligibility_category": "bpl_family"}
- "Hu Gujarat thi chu, maari income 2 lakh che" (Gujarati, "I'm from Gujarat, my income is 2
  lakh") -> {"state_residency": "Gujarat", "annual_income_inr": 200000}
- "No I don't get any pension from anywhere else" -> {"receives_other_government_pension": false}
""".strip()


class Sarvam105BReasoningProvider(ReasoningProvider):
    MODEL = "sarvam-105b"

    def __init__(self, api_key: str):
        self._client = AsyncSarvamAI(api_subscription_key=api_key)

    async def extract(
        self, text: str, field_specs: dict[str, FieldSpec], *, context: str | None = None
    ) -> dict[str, Any]:
        user_content = f"The assistant just asked about: {context}\n\n{text}" if context else text
        try:
            response = await self._client.chat.completions(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                # This is structured extraction, not open-ended generation — the same utterance
                # should map to the same facts every time. Left at the API's default (non-zero)
                # sampling, the exact same input was observed to extract correctly ~60% of the
                # time and return nothing the rest, with no code or prompt difference at all.
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "extracted_facts", "schema": _build_json_schema(field_specs)},
                },
            )
        except ApiError as e:
            raise NLURequestError(str(e), request_id=_request_id(e), status_code=e.status_code) from e

        content = response.choices[0].message.content
        if content is None:
            # Observed in practice on utterances with nothing matching any field_spec (e.g. a bare
            # negation with no corresponding boolean field) — the model has nothing valid to put
            # in the JSON schema and returns no content instead of "{}". Informationally that's the
            # same as an empty extraction (see this method's docstring: an omitted field means "not
            # mentioned"), so treat it as one rather than raising and crashing the whole turn.
            return {}

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
        if spec.description is not None:
            prop["description"] = spec.description
        properties[name] = prop

    return {"type": "object", "properties": properties, "additionalProperties": False}


def _request_id(error: ApiError) -> str | None:
    return error.body.get("request_id") if isinstance(error.body, dict) else None