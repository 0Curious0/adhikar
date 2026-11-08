from .base import DecisionProvider
from .models import DecisionQuestion, Intent

MIN_CONFIDENCE = 0.4
"""Prism's `confidence` is 0 at an even split across every option and 1 at certainty. Below
this, the top choice isn't decisive enough to act on."""

_INTENT_INSTRUCTIONS = "Classify what the user's utterance is asking the voice assistant to do."

_INTENT_CRITERIA = {
    Intent.GRIEVANCE.value: (
        "The user is reporting a problem with a scheme they're already enrolled in or have "
        "applied to — a missed payment, a rejected application, a delay — or asking how to "
        "file or escalate a complaint about one."
    ),
    Intent.SCHEME_QUERY.value: (
        "The user is asking a question about a welfare scheme itself: whether they qualify, "
        "what the benefit is, or how to apply. This is a question about a scheme, not a "
        "complaint about one, and not a request to change which scheme is being discussed."
    ),
    Intent.UPDATE_INFO.value: (
        "The user is stating or correcting a fact about themselves (age, income, state, "
        "marital status, category, etc.), or explicitly asking to talk about a different "
        "scheme or topic than the one currently being discussed."
    ),
    Intent.UNRELATED.value: (
        "The utterance has nothing to do with welfare schemes, eligibility, or grievances — "
        "small talk, silence, noise, or something entirely off-topic."
    ),
}


async def classify_intent(
    provider: DecisionProvider,
    transcript: str,
    *,
    pinned_scheme_id: str | None,
    min_confidence: float = MIN_CONFIDENCE,
) -> Intent | None:
    """Classify `transcript` into one of `Intent`, or None if Prism isn't confident enough.

    `pinned_scheme_id` is passed alongside the transcript as context (not baked into the
    static `criteria` text) so Prism can tell "asking about a scheme for the first time"
    (SCHEME_QUERY) apart from "asking to switch away from the scheme already pinned"
    (UPDATE_INFO) — a distinction that depends on conversation state, not just the utterance.
    """
    state = {"utterance": transcript, "currently_discussing_scheme": pinned_scheme_id}
    question = DecisionQuestion(instructions=_INTENT_INSTRUCTIONS, criteria=_INTENT_CRITERIA)

    answers = await provider.decide(state, {"intent": question})
    answer = answers["intent"]

    if answer.confidence < min_confidence:
        return None
    return Intent(answer.choice)


async def classify_scheme(
    provider: DecisionProvider,
    transcript: str,
    scheme_descriptions: dict[str, str],
    *,
    min_confidence: float = MIN_CONFIDENCE,
) -> str | None:
    """Pick which scheme_id in `scheme_descriptions` the transcript is about.

    `scheme_descriptions` maps scheme_id to a short description, used as Prism's `criteria`.
    Returns None if Prism isn't confident enough — the caller should ask a clarifying question
    rather than guess which scheme the user means.
    """
    question = DecisionQuestion(
        instructions="Which welfare scheme is the user's utterance about?",
        criteria=scheme_descriptions,
    )

    answers = await provider.decide(transcript, {"scheme": question})
    answer = answers["scheme"]

    if answer.confidence < min_confidence:
        return None
    return answer.choice
