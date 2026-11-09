from typing import Any

from ..nlg import ConversationProvider
from ..nlu import (
    DecisionProvider,
    Intent,
    ReasoningProvider,
    build_field_specs,
    classify_intent,
    classify_requested_scheme,
    classify_scheme,
    extract_entities,
)
from ..nlu.models import FieldSpec
from ..schemes import EligibilityResult, EligibilityRule, EligibilityStatus, RuleCheck, RuleState, SchemeDocument, evaluate
from .activity import ActivityLogStore
from .profile import ProfileStore, UserProfile, merge_facts, pin_scheme, set_last_asked_fields


class Orchestrator:
    def __init__(
        self,
        *,
        profile_store: ProfileStore,
        activity_log: ActivityLogStore,
        decision_provider: DecisionProvider,
        reasoning_provider: ReasoningProvider,
        conversation_provider: ConversationProvider,
        schemes: dict[str, SchemeDocument],
    ):
        self._profile_store = profile_store
        self._activity_log = activity_log
        self._decision_provider = decision_provider
        self._reasoning_provider = reasoning_provider
        self._conversation_provider = conversation_provider
        self._schemes = schemes
        # The global set (every scheme's fields combined) is only used before any scheme is
        # pinned, when it's not yet known which scheme's fields are even relevant. Once a scheme
        # is pinned, extraction is scoped to just that scheme's own fields (`_field_specs_by_scheme`)
        # — the combined global schema, tried first, both missed real facts and fabricated
        # unrelated ones (default-looking values the transcript never stated) on the same exact
        # input across repeated calls, almost certainly from sheer schema size/complexity.
        self._field_specs = build_field_specs(schemes)
        self._field_specs_by_scheme: dict[str, dict[str, FieldSpec]] = {
            scheme_id: build_field_specs({scheme_id: doc}) for scheme_id, doc in schemes.items()
        }
        self._scheme_descriptions = {
            scheme_id: doc.description.get("en") or doc.name.get("en", scheme_id) for scheme_id, doc in schemes.items()
        }

    def _log_activity_if_changed(self, profile: UserProfile, previous_scheme_id: str | None) -> None:
        """Record one "a scheme newly became this user's topic" event — skipped when the pinned
        scheme didn't actually change, so re-confirming the same scheme doesn't spam the log."""
        if profile.pinned_scheme_id is None or profile.pinned_scheme_id == previous_scheme_id:
            return
        doc = self._schemes[profile.pinned_scheme_id]
        status = evaluate(doc, profile.facts).status.value
        self._activity_log.log(profile.user_id, scheme_id=profile.pinned_scheme_id, eligibility_status=status)

    async def handle_turn(self, *, user_id: str, transcript: str, language_code: str) -> str | None:
        profile = self._profile_store.get(user_id)
        just_asked_about = ", ".join(profile.last_asked_fields) or None
        intent = await classify_intent(
            self._decision_provider,
            transcript,
            pinned_scheme_id=profile.pinned_scheme_id,
            just_asked_about=just_asked_about,
        )

        if intent is None:
            return await self._conversation_provider.reply(
                system_prompt="You did not understand the user. Briefly ask them to repeat themselves.",
                user_message=transcript,
                language_code=language_code,
            )
        if intent == Intent.UNRELATED:
            # A real, same-language reply rather than silence (the original design — "low-value
            # turns shouldn't cost a TTS call" — was a deliberate call, reversed on request: a
            # user who gets no response at all, visible or spoken, reasonably assumes the app is
            # broken rather than "this wasn't about a scheme," especially over voice where
            # there's no text on screen to fall back on reading.
            return await self._conversation_provider.reply(
                system_prompt=(
                    "The user's utterance has nothing to do with government welfare schemes, "
                    "eligibility, or grievances. Briefly and politely let them know this "
                    "assistant can only help with those topics."
                ),
                user_message=transcript,
                language_code=language_code,
            )
        if intent == Intent.UPDATE_INFO:
            return await self._handle_update_info(profile, transcript, language_code)
        return await self._handle_scheme_turn(profile, transcript, language_code, intent)

    async def _handle_update_info(self, profile: UserProfile, transcript: str, language_code: str) -> str | None:
        previous_scheme_id = profile.pinned_scheme_id
        field_specs = (
            self._field_specs_by_scheme[profile.pinned_scheme_id]
            if profile.pinned_scheme_id is not None
            else self._field_specs
        )
        just_asked_about = ", ".join(profile.last_asked_fields) or None
        # Two separate calls, not one combined extraction: picking which scheme (a fixed,
        # known list) is a decision for Prism, same as classify_scheme — folding it into 105B's
        # open-ended facts extraction was tried first and made both parts less reliable.
        facts = await extract_entities(self._reasoning_provider, transcript, field_specs, context=just_asked_about)
        requested_scheme, is_switch_attempt = await classify_requested_scheme(
            self._decision_provider, transcript, self._scheme_descriptions, pinned_scheme_id=profile.pinned_scheme_id
        )

        if is_switch_attempt and requested_scheme is None:
            # Wants to leave the current scheme but didn't name — or didn't confidently
            # resolve — a replacement. Ask which one instead of silently continuing the old
            # scheme (the original gap this used to fall into). `facts` is ignored here too: an
            # utterance that's actually about switching has nothing real to extract, and 105B
            # was observed fabricating one on exactly these turns rather than reliably returning
            # nothing.
            self._profile_store.save(set_last_asked_fields(profile, []))
            options = "; ".join(
                f"{sid}: {desc}" for sid, desc in self._scheme_descriptions.items() if sid != profile.pinned_scheme_id
            )
            return await self._conversation_provider.reply(
                system_prompt=(
                    "The user wants to stop discussing the current scheme but didn't say which "
                    "one to switch to instead. Ask them which welfare scheme they'd like to "
                    "talk about, briefly listing the options."
                ),
                user_message=f"Options: {options}",
                language_code=language_code,
            )

        if not facts and not is_switch_attempt:
            # Separate providers can still disagree — Prism's intent call judged this an
            # UPDATE_INFO turn but neither the facts extraction nor the scheme-switch decision
            # found anything concrete. Going silent here would be a dead end for the user; fall
            # back to continuing whatever's already in progress rather than no-op'ing.
            if profile.pinned_scheme_id is None:
                return await self._conversation_provider.reply(
                    system_prompt="You did not understand the user. Briefly ask them to repeat themselves.",
                    user_message=transcript,
                    language_code=language_code,
                )
            return await self._handle_scheme_query(self._schemes[profile.pinned_scheme_id], profile, language_code)

        # A switch turn gets its `facts` discarded, not merged: an utterance that's purely
        # "switch to X" has nothing real to extract, and 105B was observed fabricating multiple
        # facts (an age, a state, booleans) on exactly these turns rather than reliably returning
        # {} — which then got evaluated as if the user had actually stated them, up to and
        # including a confidently wrong "you're not eligible, you live in <fabricated state>"
        # verdict in the very same reply. The switch-detection half was never the problem.
        facts_to_record = facts if not is_switch_attempt else {}
        if facts_to_record:
            profile = merge_facts(profile, facts_to_record)
        if requested_scheme is not None:
            profile = pin_scheme(profile, requested_scheme)
        self._profile_store.save(profile)
        self._log_activity_if_changed(profile, previous_scheme_id)

        update_summary = _describe_update(facts_to_record, requested_scheme, self._scheme_descriptions)

        if profile.pinned_scheme_id is None:
            self._profile_store.save(set_last_asked_fields(profile, []))
            return await self._conversation_provider.reply(
                system_prompt=(
                    "The user just gave the assistant some information, or asked to change which "
                    "scheme is being discussed. Briefly confirm what was recorded, in one short, "
                    "warm sentence."
                ),
                user_message=update_summary,
                language_code=language_code,
            )

        # A scheme is already pinned, so this update may have just filled in (or invalidated) a
        # fact the eligibility check was waiting on — continue the flow in the same reply instead
        # of leaving the user to ask again.
        doc = self._schemes[profile.pinned_scheme_id]
        eligibility_system, eligibility_user, asked_fields = _build_eligibility_message(doc, profile)
        self._profile_store.save(set_last_asked_fields(profile, asked_fields))
        return await self._conversation_provider.reply(
            system_prompt=(
                "First, briefly confirm what the user just told you, or that the topic changed, "
                "in one short sentence. Then continue: " + eligibility_system
            ),
            user_message=f"What changed: {update_summary}\n{eligibility_user}",
            language_code=language_code,
        )

    async def _handle_scheme_turn(
        self, profile: UserProfile, transcript: str, language_code: str, intent: Intent
    ) -> str | None:
        if profile.pinned_scheme_id is None:
            scheme_id = await classify_scheme(self._decision_provider, transcript, self._scheme_descriptions)
            if scheme_id is None:
                options = "; ".join(f"{sid}: {desc}" for sid, desc in self._scheme_descriptions.items())
                return await self._conversation_provider.reply(
                    system_prompt="Ask the user which welfare scheme they want to talk about, briefly listing the options.",
                    user_message=f"Options: {options}",
                    language_code=language_code,
                )
            previous_scheme_id = profile.pinned_scheme_id
            profile = pin_scheme(profile, scheme_id)
            self._profile_store.save(profile)
            self._log_activity_if_changed(profile, previous_scheme_id)
        else:
            scheme_id = profile.pinned_scheme_id

        doc = self._schemes[scheme_id]
        if intent == Intent.SCHEME_QUERY:
            return await self._handle_scheme_query(doc, profile, language_code)
        return await self._handle_grievance(doc, profile, transcript, language_code)

    async def _handle_scheme_query(self, doc: SchemeDocument, profile: UserProfile, language_code: str) -> str:
        system_prompt, user_message, asked_fields = _build_eligibility_message(doc, profile)
        self._profile_store.save(set_last_asked_fields(profile, asked_fields))
        return await self._conversation_provider.reply(
            system_prompt=system_prompt, user_message=user_message, language_code=language_code
        )

    async def _handle_grievance(self, doc: SchemeDocument, profile: UserProfile, transcript: str, language_code: str) -> str:
        scheme_name = doc.name.get("en", doc.scheme_id)
        # A grievance reply isn't asking about any eligibility field — clear it so a later,
        # unrelated short reply doesn't get misattributed to a question that's no longer live.
        self._profile_store.save(set_last_asked_fields(profile, []))

        if doc.grievance is None:
            return await self._conversation_provider.reply(
                system_prompt=f"Apologize that grievance information for {scheme_name} isn't available yet. Keep it brief.",
                user_message=f"Scheme: {scheme_name}",
                language_code=language_code,
            )

        channels = "; ".join(f"{c.name} ({c.type})" for c in doc.grievance.channels)
        return await self._conversation_provider.reply(
            system_prompt=(
                f"Help the user file or escalate a grievance about {scheme_name}. Use the "
                "channels and instructions given to tell them the best way forward, briefly and "
                "in simple spoken language. Pick whichever channel best matches what they "
                "described, if more than one is given."
            ),
            user_message=(
                f"User's complaint: {transcript}\n"
                f"Scheme: {scheme_name}\n"
                f"Channels: {channels}\n"
                f"Instructions: {doc.grievance.instructions}"
            ),
            language_code=language_code,
        )


def _build_eligibility_message(doc: SchemeDocument, profile: UserProfile) -> tuple[str, str, list[str]]:
    """Returns (system_prompt, user_message, asked_fields) describing the scheme's current
    eligibility status for `profile` — shared by the first SCHEME_QUERY turn and by
    UPDATE_INFO's continuation once a scheme is already pinned, so both phrase the same status
    the same way. `asked_fields` is the flat list of fields this reply is actually asking about
    (empty unless `MISSING_FIELDS`) — callers persist it via `set_last_asked_fields` so the next
    turn's `classify_intent`/`extract_entities` know what a short or vague reply might be
    answering, instead of having to guess blind from the bare utterance alone."""
    result = evaluate(doc, profile.facts)
    scheme_name = doc.name.get("en", doc.scheme_id)

    if result.status == EligibilityStatus.MISSING_FIELDS:
        system_prompt = (
            f"Ask the user for ALL of the information below needed to check their eligibility "
            f"for {scheme_name}, combined into ONE natural question — don't ask one piece at a "
            "time across multiple turns, that's tedious for a voice conversation. For any line "
            "that offers multiple fields as alternatives, make clear the user only needs to "
            "answer one of them, not all. Keep it as brief as possible while covering everything. "
            "For anything that's really a yes/no fact, don't phrase it as a plain yes/no "
            "question — phrase it so a natural reply restates the fact itself (prefer 'please "
            "tell me whether you currently receive any other government pension' over 'do you "
            "receive any other pension?'). The next turn is understood on its own, with no "
            "memory of which question was just asked, so a bare 'yes' or 'no' can't be matched "
            "back to what it was answering — the reply has to carry that context itself."
        )
        asked_fields = [
            check.rule.field
            for group in result.missing_groups
            for check in group
            if check.state == RuleState.MISSING
        ]
        return system_prompt, _describe_missing_groups(result.missing_groups), asked_fields

    if result.status == EligibilityStatus.ELIGIBLE:
        system_prompt = (
            f"Tell the user they ARE eligible for {scheme_name}. Briefly describe the main "
            "benefit using the details given, in an encouraging tone."
        )
        return system_prompt, f"Scheme: {scheme_name}. Benefits: {doc.benefits}", []

    system_prompt = (
        f"Tell the user they are NOT currently eligible for {scheme_name}. Kindly and briefly "
        "explain which requirement(s) they didn't meet, using the reasons given."
    )
    return system_prompt, f"Scheme: {scheme_name}. Reasons: {_describe_failed_groups(result.failed_groups)}", []


def _describe_update(facts: dict[str, Any], requested_scheme: str | None, scheme_descriptions: dict[str, str]) -> str:
    parts = [f"{field}: {value}" for field, value in facts.items()]
    if requested_scheme is not None:
        scheme_name = scheme_descriptions.get(requested_scheme, requested_scheme)
        parts.append(f"switched topic to: {scheme_name}")
    return "; ".join(parts)


def _describe_missing_groups(groups: list[list[RuleCheck]]) -> str:
    return "\n".join(f"- {_describe_missing_group(group)}" for group in groups)


def _describe_missing_group(group: list[RuleCheck]) -> str:
    missing_fields = [check.rule.field for check in group if check.state == RuleState.MISSING]
    failed_fields = [check.rule.field for check in group if check.state == RuleState.FAIL]

    if len(missing_fields) > 1:
        description = "The user only needs to satisfy ONE of these, not all: " + " OR ".join(missing_fields)
    else:
        description = f"Ask about: {missing_fields[0]}"

    if failed_fields:
        description += f". Already checked and did not qualify via: {', '.join(failed_fields)} — no need to ask about those again."

    return description


def _describe_failed_groups(failed_groups: list[list[EligibilityRule]]) -> str:
    descriptions = []
    for group in failed_groups:
        reasons = [rule.note or f"{rule.field} {rule.operator.value} {rule.value}" for rule in group]
        if len(reasons) > 1:
            descriptions.append("none of the following alternatives were met: " + " OR ".join(reasons))
        else:
            descriptions.append(reasons[0])
    return "; ".join(descriptions)