from sarvamai import AsyncSarvamAI
from sarvamai.core.api_error import ApiError

from .base import ConversationProvider
from .exceptions import NLGError, NLGRequestError

# The 10 languages Sarvam and Gnani both support (their intersection) — Sarvam additionally
# supports Odia, but Gnani's STT/TTS does not, so it's left out here to keep the voice pipeline
# end-to-end in every language this app offers.
_LANGUAGE_NAMES = {
    "hi-IN": "Hindi",
    "en-IN": "English",
    "bn-IN": "Bengali",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "pa-IN": "Punjabi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
}


class Sarvam105BConversationsProvider(ConversationProvider):
    MODEL = "sarvam-105b-conversations"

    def __init__(self, api_key: str):
        self._client = AsyncSarvamAI(api_subscription_key=api_key)

    async def reply(self, *, system_prompt: str, user_message: str, language_code: str) -> str:
        if language_code not in _LANGUAGE_NAMES:
            raise NLGError(f"unsupported language_code {language_code!r}")

        full_system_prompt = (
            f"{system_prompt}\n\n"
            f"Respond only in {_LANGUAGE_NAMES[language_code]}, in a natural, colloquial, "
            "spoken style suitable for a voice assistant talking to a low-literacy user. Do "
            "not mix in other languages or scripts, and do not add commentary outside the reply."
        )

        try:
            response = await self._client.chat.completions(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
        except ApiError as e:
            raise NLGRequestError(str(e), request_id=_request_id(e), status_code=e.status_code) from e

        content = response.choices[0].message.content
        if content is None:
            raise NLGError("conversational model returned no content")
        return content


def _request_id(error: ApiError) -> str | None:
    return error.body.get("request_id") if isinstance(error.body, dict) else None