from .base import DecisionProvider
from .models import DecisionQuestion, Intent

MIN_CONFIDENCE = 0.4
"""Prism's `confidence` is 0 at an even split across every option and 1 at certainty. Below
this, the top choice isn't decisive enough to act on."""

_INTENT_INSTRUCTIONS = "Classify what the user's utterance is asking the voice assistant to do."

_INTENT_CRITERIA = {
    Intent.GRIEVANCE.value: (
        "The user is reporting a problem with a scheme they're already enrolled in, have "
        "applied to, or were promised — a missed or delayed payment, a rejected or stuck "
        "application, an incorrect benefit amount — or asking how or where to file or escalate "
        "a complaint about one. Examples: 'my pension hasn't come this month', 'my application "
        "got rejected, what do I do', 'how do I complain about this'. Not this for a first-time "
        "question about whether they qualify — that's SCHEME_QUERY, not a complaint yet."
    ),
    Intent.SCHEME_QUERY.value: (
        "The user is asking about a welfare scheme itself — whether they qualify, what the "
        "benefit is, how much it pays, or how to apply — either about the scheme already named "
        "in `currently_discussing_scheme`, or naming a scheme for the first time when none is "
        "pinned yet. Examples: 'am I eligible', 'how much money do I get', 'how do I apply'. "
        "NOT this if the utterance names or clearly implies a DIFFERENT scheme than "
        "`currently_discussing_scheme`, or explicitly rejects/wants to leave the current one — "
        "that's UPDATE_INFO instead, even though it's still phrased as a question about a "
        "scheme. Also NOT this if `just_asked_about` names specific fields and the utterance "
        "plausibly answers one of them — that's UPDATE_INFO too, even if the wording happens to "
        "echo scheme-related vocabulary (see UPDATE_INFO's criteria for why)."
    ),
    Intent.UPDATE_INFO.value: (
        "Either of two things, both routed here: (1) the user is stating, correcting, or "
        "answering a question about a fact about themselves — age, income, state, marital "
        "status, category, documents, a plain yes/no answer to something just asked, etc. "
        "Examples: 'I'm 45', 'my income is 2 lakh', 'no, I don't have a BPL card'. If "
        "`just_asked_about` names specific fields, treat this as the strongest possible signal: "
        "an utterance that plausibly answers any of those fields — even just 'yes', 'no', a "
        "number, or a short phrase with no scheme-related words in it at all — is UPDATE_INFO, "
        "never SCHEME_QUERY, no matter how much it also sounds like it could be describing the "
        "scheme's own criteria back (e.g. if `just_asked_about` includes a field about owning "
        "farmland, 'yes, my family owns farmland' is the user ANSWERING that field, not asking a "
        "fresh question about land rules). (2) The user is asking to change which scheme is "
        "being discussed, away from `currently_discussing_scheme` — either by naming a different "
        "scheme, or by rejecting the current one even without naming a replacement yet. "
        "Examples: 'no, tell me about PM-KISAN instead', 'actually I meant to ask about the "
        "pension scheme', 'change the scheme', 'no, not this one', 'can we talk about something "
        "else'. This applies even when phrased as a question ('what about PM-KISAN?') — the "
        "deciding factor is that it's about a different topic than `currently_discussing_scheme`, "
        "or a rejection of it, not the grammatical form of the sentence."
    ),
    Intent.UNRELATED.value: (
        "The utterance has nothing to do with welfare schemes, eligibility, grievances, or the "
        "user's own facts — small talk ('hello', 'thank you'), silence, background noise, or "
        "something entirely off-topic. If genuinely unsure between this and one of the other "
        "three, prefer the other one — this option is only for utterances with no actionable "
        "content at all."
    ),
}


async def classify_intent(
    provider: DecisionProvider,
    transcript: str,
    *,
    pinned_scheme_id: str | None,
    just_asked_about: str | None = None,
    min_confidence: float = MIN_CONFIDENCE,
) -> Intent | None:
    """Classify `transcript` into one of `Intent`, or None if Prism isn't confident enough.

    `pinned_scheme_id` is passed alongside the transcript as context (not baked into the
    static `criteria` text) so Prism can tell "asking about a scheme for the first time"
    (SCHEME_QUERY) apart from "asking to switch away from the scheme already pinned"
    (UPDATE_INFO) — a distinction that depends on conversation state, not just the utterance.

    `just_asked_about` (optional): comma-joined field names the assistant's last reply actually
    asked about (see `Orchestrator._build_eligibility_message`'s asked-fields bookkeeping).
    Without this, a direct answer to a just-asked question ("yes, my family owns farmland") can
    get misrouted to SCHEME_QUERY purely because its vocabulary overlaps with the scheme's own
    criteria — Prism has no way to tell "describing my own situation" apart from "asking about
    the scheme's rules" from the utterance alone.
    """
    state = {
        "utterance": transcript,
        "currently_discussing_scheme": pinned_scheme_id,
        "just_asked_about": just_asked_about,
    }
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


_NOT_SWITCHING = "not_switching"
_SWITCHING_UNSPECIFIED = "switching_unspecified"


async def classify_requested_scheme(
    provider: DecisionProvider,
    transcript: str,
    scheme_descriptions: dict[str, str],
    *,
    pinned_scheme_id: str | None,
    min_confidence: float = MIN_CONFIDENCE,
) -> tuple[str | None, bool]:
    """On an UPDATE_INFO turn, decide whether the user is asking to switch to a different
    scheme, and which one — a fixed-choice decision, so this belongs to Prism, not 105B's
    open-ended entity extraction (105B was tried first: combined with the rest of the
    demographic-facts schema, it both missed real scheme switches and fabricated unrelated
    facts with default-looking values on the same exact input across repeated calls).

    Returns `(scheme_id, is_switch_attempt)`. `is_switch_attempt` is True whenever the user is
    trying to leave `pinned_scheme_id` at all, even if no specific replacement was named or
    confidently resolved (`scheme_id` is then `None`) — callers use it for two things a plain
    `scheme_id` can't distinguish on its own: (1) whether to discard this turn's extracted
    facts, since an utterance that's actually about switching schemes has nothing real for 105B
    to extract, and 105B was observed fabricating facts on exactly these turns rather than
    reliably returning nothing; (2) whether to ask "which scheme?" instead of silently
    continuing the old one when the switch itself didn't resolve.

    An UPDATE_INFO turn is just as often a plain fact statement with no scheme mentioned at all
    ("I'm 45"), so the real scheme options are joined by two meta-options rather than forcing
    Prism to pick a real scheme regardless — without them, Prism's `decide()` always returns a
    top choice among whatever options it's given, which would turn every fact-only utterance
    into a spurious scheme switch. `_SWITCHING_UNSPECIFIED` ("no, not this one", "can we talk
    about something else") and `_NOT_SWITCHING` (an actual fact statement) look identical if
    collapsed into one catch-all option — tried first, and found to send clear rejections down
    the same path as genuine facts — so they're kept as two separate, explicit options instead.
    `pinned_scheme_id` itself is excluded from the real scheme options: by the time intent
    classification routed here as UPDATE_INFO rather than SCHEME_QUERY, the user is already
    known not to just be continuing the current topic.
    """
    criteria = {
        sid: desc for sid, desc in scheme_descriptions.items() if sid != pinned_scheme_id
    }
    criteria[_SWITCHING_UNSPECIFIED] = (
        "The user wants to stop discussing the current scheme, or switch away from it, but "
        "does not clearly name or imply which other scheme they mean. Examples: 'no, not this "
        "one', 'can we talk about something else', 'change the scheme'."
    )
    criteria[_NOT_SWITCHING] = (
        "The user is not trying to switch schemes at all — they're stating or correcting a "
        "fact about themselves, or asking something about the scheme already being discussed."
    )
    question = DecisionQuestion(
        instructions="Is the user explicitly asking to switch to a different welfare scheme, and if so, which one?",
        criteria=criteria,
    )

    answers = await provider.decide(transcript, {"requested_scheme": question})
    answer = answers["requested_scheme"]

    if answer.choice == _NOT_SWITCHING:
        return None, False
    if answer.choice == _SWITCHING_UNSPECIFIED or answer.confidence < min_confidence:
        return None, True
    return answer.choice, True
