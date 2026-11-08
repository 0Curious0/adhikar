from typing import Any

from adhikar.dialogue.orchestrator import Orchestrator
from adhikar.dialogue.profile import SQLiteProfileStore, UserProfile
from adhikar.nlg.base import ConversationProvider
from adhikar.nlu.base import DecisionProvider, DecisionState, ReasoningProvider
from adhikar.nlu.models import ChoiceAnswer, DecisionQuestion, FieldSpec
from adhikar.schemes.models import SchemeDocument

BASE = {"schema_version": "1.0.0", "jurisdiction": {"level": "central", "country": "IN"}}


def _scheme_a() -> SchemeDocument:
    return SchemeDocument.model_validate(
        {
            **BASE,
            "scheme_id": "scheme_a",
            "name": {"en": "Scheme A"},
            "eligibility_rules": [
                {
                    "rule_id": "A1",
                    "field": "age_years",
                    "operator": "greater_than_or_equal",
                    "value": 18,
                    "verification_status": "verified",
                    "note": "Must be an adult.",
                }
            ],
            "benefits": {"amount": {"value": 1000, "currency": "INR"}},
        }
    )


def _scheme_b() -> SchemeDocument:
    return SchemeDocument.model_validate(
        {
            **BASE,
            "scheme_id": "scheme_b",
            "name": {"en": "Scheme B"},
            "eligibility_rules": [
                {
                    "rule_id": "B1",
                    "field": "annual_income_inr",
                    "operator": "less_than",
                    "value": 48000,
                    "verification_status": "verified",
                    "rule_group": "FIN",
                },
                {
                    "rule_id": "B2",
                    "field": "special_eligibility_category",
                    "operator": "in",
                    "value": ["bpl_family"],
                    "verification_status": "verified",
                    "rule_group": "FIN",
                },
                {
                    "rule_id": "B3",
                    "field": "state_residency",
                    "operator": "equals",
                    "value": "Rajasthan",
                    "verification_status": "verified",
                },
            ],
            "grievance": {
                "channels": [{"name": "Portal", "type": "online", "verification_status": "verified"}],
                "instructions": "File online.",
                "verification_status": "verified",
            },
        }
    )


SCHEMES = {"scheme_a": _scheme_a(), "scheme_b": _scheme_b()}


class FakeDecisionProvider(DecisionProvider):
    def __init__(self, answers: dict[str, ChoiceAnswer]):
        self._answers = answers
        self.calls: list[tuple[DecisionState, dict[str, DecisionQuestion]]] = []

    async def decide(self, state: DecisionState, questions: dict[str, DecisionQuestion]) -> dict[str, ChoiceAnswer]:
        self.calls.append((state, questions))
        return {question_id: self._answers[question_id] for question_id in questions}


class FakeReasoningProvider(ReasoningProvider):
    def __init__(self, result: dict[str, Any]):
        self._result = result
        self.calls: list[tuple[str, dict[str, FieldSpec]]] = []

    async def extract(self, text: str, field_specs: dict[str, FieldSpec]) -> dict[str, Any]:
        self.calls.append((text, field_specs))
        return self._result


class FakeConversationProvider(ConversationProvider):
    def __init__(self, reply_text: str = "ok"):
        self.reply_text = reply_text
        self.calls: list[dict[str, str]] = []

    async def reply(self, *, system_prompt: str, user_message: str, language_code: str) -> str:
        self.calls.append({"system_prompt": system_prompt, "user_message": user_message, "language_code": language_code})
        return self.reply_text


def _orchestrator(
    tmp_path,
    *,
    decision_answers: dict[str, ChoiceAnswer],
    reasoning_result: dict[str, Any] | None = None,
    reply_text: str = "ok",
) -> tuple[Orchestrator, SQLiteProfileStore, FakeConversationProvider]:
    store = SQLiteProfileStore(tmp_path / "profiles.db")
    conversation = FakeConversationProvider(reply_text)
    orchestrator = Orchestrator(
        profile_store=store,
        decision_provider=FakeDecisionProvider(decision_answers),
        reasoning_provider=FakeReasoningProvider(reasoning_result or {}),
        conversation_provider=conversation,
        schemes=SCHEMES,
    )
    return orchestrator, store, conversation


async def test_unrelated_returns_none_and_touches_nothing(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="unrelated", confidence=0.9, probabilities={})}
    )

    result = await orchestrator.handle_turn(user_id="u1", transcript="lol random", language_code="en-IN")

    assert result is None
    assert conversation.calls == []
    assert store.get("u1") == UserProfile(user_id="u1")


async def test_low_confidence_intent_asks_to_repeat(tmp_path):
    orchestrator, _, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="scheme_query", confidence=0.05, probabilities={})}
    )

    result = await orchestrator.handle_turn(user_id="u1", transcript="hmm", language_code="en-IN")

    assert result == "ok"
    assert "repeat" in conversation.calls[0]["system_prompt"].lower()


async def test_update_info_merges_facts_and_confirms(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path,
        decision_answers={"intent": ChoiceAnswer(choice="update_info", confidence=0.9, probabilities={})},
        reasoning_result={"age_years": 45},
        reply_text="Got it, you're 45.",
    )

    result = await orchestrator.handle_turn(user_id="u1", transcript="I'm 45", language_code="en-IN")

    assert result == "Got it, you're 45."
    assert store.get("u1").facts == {"age_years": 45}
    assert "age_years: 45" in conversation.calls[0]["user_message"]


async def test_update_info_with_pinned_scheme_continues_with_next_missing_field(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path,
        decision_answers={"intent": ChoiceAnswer(choice="update_info", confidence=0.9, probabilities={})},
        reasoning_result={"annual_income_inr": 60000},
    )
    store.save(UserProfile(user_id="u1", pinned_scheme_id="scheme_b"))

    await orchestrator.handle_turn(user_id="u1", transcript="my income is 60000", language_code="en-IN")

    message = conversation.calls[0]["user_message"]
    assert "annual_income_inr: 60000" in message
    assert "Ask about: special_eligibility_category" in message


async def test_update_info_with_pinned_scheme_continues_with_eligible_result(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path,
        decision_answers={"intent": ChoiceAnswer(choice="update_info", confidence=0.9, probabilities={})},
        reasoning_result={"age_years": 20},
    )
    store.save(UserProfile(user_id="u1", pinned_scheme_id="scheme_a"))

    await orchestrator.handle_turn(user_id="u1", transcript="I'm 20", language_code="en-IN")

    assert "ARE eligible" in conversation.calls[0]["system_prompt"]
    assert "age_years: 20" in conversation.calls[0]["user_message"]


async def test_update_info_with_requested_scheme_pins_scheme(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path,
        decision_answers={"intent": ChoiceAnswer(choice="update_info", confidence=0.9, probabilities={})},
        reasoning_result={"requested_scheme": "scheme_b"},
    )

    await orchestrator.handle_turn(user_id="u1", transcript="actually ask about scheme b", language_code="en-IN")

    assert store.get("u1").pinned_scheme_id == "scheme_b"
    assert "switched topic to: Scheme B" in conversation.calls[0]["user_message"]


async def test_update_info_with_nothing_extracted_is_a_silent_no_op(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path,
        decision_answers={"intent": ChoiceAnswer(choice="update_info", confidence=0.9, probabilities={})},
        reasoning_result={},
    )

    result = await orchestrator.handle_turn(user_id="u1", transcript="umm", language_code="en-IN")

    assert result is None
    assert conversation.calls == []
    assert store.get("u1") == UserProfile(user_id="u1")


async def test_scheme_query_classifies_scheme_when_unpinned_then_asks_missing_field(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path,
        decision_answers={
            "intent": ChoiceAnswer(choice="scheme_query", confidence=0.9, probabilities={}),
            "scheme": ChoiceAnswer(choice="scheme_a", confidence=0.9, probabilities={}),
        },
    )

    await orchestrator.handle_turn(user_id="u1", transcript="am I eligible for scheme a?", language_code="en-IN")

    assert store.get("u1").pinned_scheme_id == "scheme_a"
    assert "Ask about: age_years" in conversation.calls[0]["user_message"]


async def test_scheme_query_clarifies_when_scheme_unsure_and_does_not_pin(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path,
        decision_answers={
            "intent": ChoiceAnswer(choice="scheme_query", confidence=0.9, probabilities={}),
            "scheme": ChoiceAnswer(choice="scheme_a", confidence=0.05, probabilities={}),
        },
    )

    await orchestrator.handle_turn(user_id="u1", transcript="am I eligible?", language_code="en-IN")

    assert store.get("u1").pinned_scheme_id is None
    assert "Scheme A" in conversation.calls[0]["user_message"]
    assert "Scheme B" in conversation.calls[0]["user_message"]


async def test_scheme_query_reuses_pinned_scheme_without_reclassifying(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="scheme_query", confidence=0.9, probabilities={})}
    )
    store.save(UserProfile(user_id="u1", pinned_scheme_id="scheme_a", facts={"age_years": 20}))

    result = await orchestrator.handle_turn(user_id="u1", transcript="am I eligible?", language_code="en-IN")

    # no KeyError from the fake decision provider looking up a "scheme" answer means
    # classify_scheme was never called, since only "intent" was registered.
    assert "ARE eligible" in conversation.calls[0]["system_prompt"]
    assert result == "ok"


async def test_scheme_query_missing_fields_combines_all_groups_into_one_question(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="scheme_query", confidence=0.9, probabilities={})}
    )
    store.save(UserProfile(user_id="u1", pinned_scheme_id="scheme_b"))

    await orchestrator.handle_turn(user_id="u1", transcript="am I eligible?", language_code="en-IN")

    system_prompt = conversation.calls[0]["system_prompt"]
    message = conversation.calls[0]["user_message"]
    # scheme_b has two unresolved groups: the FIN OR-group (income/category) and the
    # independent state_residency rule — both should be surfaced in one combined message.
    assert "ONE natural question" in system_prompt
    assert "don't ask one piece at a time" in system_prompt
    assert "ONE of these, not all" in message
    assert "annual_income_inr" in message
    assert "special_eligibility_category" in message
    assert "state_residency" in message


async def test_scheme_query_eligible_reports_benefits(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="scheme_query", confidence=0.9, probabilities={})}
    )
    store.save(UserProfile(user_id="u1", pinned_scheme_id="scheme_a", facts={"age_years": 20}))

    await orchestrator.handle_turn(user_id="u1", transcript="am I eligible?", language_code="en-IN")

    assert "ARE eligible" in conversation.calls[0]["system_prompt"]
    assert "1000" in conversation.calls[0]["user_message"]


async def test_scheme_query_not_eligible_describes_reason(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="scheme_query", confidence=0.9, probabilities={})}
    )
    store.save(UserProfile(user_id="u1", pinned_scheme_id="scheme_a", facts={"age_years": 10}))

    await orchestrator.handle_turn(user_id="u1", transcript="am I eligible?", language_code="en-IN")

    message = conversation.calls[0]["user_message"]
    assert "NOT currently eligible" in conversation.calls[0]["system_prompt"]
    assert "Must be an adult." in message


async def test_scheme_query_not_eligible_with_failed_or_group_phrases_as_alternatives(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="scheme_query", confidence=0.9, probabilities={})}
    )
    store.save(
        UserProfile(
            user_id="u1",
            pinned_scheme_id="scheme_b",
            facts={"annual_income_inr": 60000, "special_eligibility_category": "none"},
        )
    )

    await orchestrator.handle_turn(user_id="u1", transcript="am I eligible?", language_code="en-IN")

    assert "none of the following alternatives were met" in conversation.calls[0]["user_message"]


async def test_grievance_uses_channels_instructions_and_transcript(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="grievance", confidence=0.9, probabilities={})}
    )
    store.save(UserProfile(user_id="u1", pinned_scheme_id="scheme_b"))

    await orchestrator.handle_turn(user_id="u1", transcript="my payment never came", language_code="en-IN")

    message = conversation.calls[0]["user_message"]
    assert "Portal" in message
    assert "File online." in message
    assert "my payment never came" in message


async def test_grievance_without_grievance_info_apologizes(tmp_path):
    orchestrator, store, conversation = _orchestrator(
        tmp_path, decision_answers={"intent": ChoiceAnswer(choice="grievance", confidence=0.9, probabilities={})}
    )
    store.save(UserProfile(user_id="u1", pinned_scheme_id="scheme_a"))

    await orchestrator.handle_turn(user_id="u1", transcript="my payment never came", language_code="en-IN")

    assert "Apologize" in conversation.calls[0]["system_prompt"]
