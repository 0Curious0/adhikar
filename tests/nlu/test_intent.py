from adhikar.nlu.base import DecisionProvider, DecisionState
from adhikar.nlu.intent import classify_intent, classify_requested_scheme, classify_scheme
from adhikar.nlu.models import ChoiceAnswer, DecisionQuestion, Intent


class FakeDecisionProvider(DecisionProvider):
    def __init__(self, answer: ChoiceAnswer):
        self._answer = answer
        self.last_state: DecisionState | None = None
        self.last_questions: dict[str, DecisionQuestion] | None = None

    async def decide(self, state: DecisionState, questions: dict[str, DecisionQuestion]) -> dict[str, ChoiceAnswer]:
        self.last_state = state
        self.last_questions = questions
        return {question_id: self._answer for question_id in questions}


async def test_classify_intent_returns_intent_when_confident():
    provider = FakeDecisionProvider(
        ChoiceAnswer(choice="scheme_query", confidence=0.8, probabilities={"scheme_query": 0.9})
    )

    result = await classify_intent(provider, "Am I eligible for PM-KISAN?", pinned_scheme_id=None)

    assert result == Intent.SCHEME_QUERY


async def test_classify_intent_returns_none_when_not_confident():
    provider = FakeDecisionProvider(
        ChoiceAnswer(choice="scheme_query", confidence=0.1, probabilities={"scheme_query": 0.3})
    )

    result = await classify_intent(provider, "hmm", pinned_scheme_id=None)

    assert result is None


async def test_classify_intent_passes_pinned_scheme_as_state_context():
    provider = FakeDecisionProvider(
        ChoiceAnswer(choice="update_info", confidence=0.9, probabilities={"update_info": 0.95})
    )

    await classify_intent(provider, "actually ask about PDS instead", pinned_scheme_id="pm_kisan")

    assert provider.last_state == {
        "utterance": "actually ask about PDS instead",
        "currently_discussing_scheme": "pm_kisan",
        "just_asked_about": None,
    }


async def test_classify_intent_passes_just_asked_about_as_state_context():
    provider = FakeDecisionProvider(
        ChoiceAnswer(choice="update_info", confidence=0.9, probabilities={"update_info": 0.95})
    )

    await classify_intent(
        provider,
        "yes, we do",
        pinned_scheme_id="pm_kisan",
        just_asked_about="family_owns_cultivable_land_as_per_state_land_records",
    )

    assert provider.last_state["just_asked_about"] == "family_owns_cultivable_land_as_per_state_land_records"


async def test_classify_intent_sends_all_four_intents_as_criteria():
    provider = FakeDecisionProvider(ChoiceAnswer(choice="unrelated", confidence=0.9, probabilities={"unrelated": 0.95}))

    await classify_intent(provider, "hello", pinned_scheme_id=None)

    question = provider.last_questions["intent"]
    assert set(question.criteria) == {"grievance", "scheme_query", "update_info", "unrelated"}


async def test_classify_scheme_returns_scheme_id_when_confident():
    provider = FakeDecisionProvider(
        ChoiceAnswer(choice="pm_kisan", confidence=0.8, probabilities={"pm_kisan": 0.9, "pds": 0.1})
    )

    result = await classify_scheme(
        provider, "Am I eligible for farmer support?", {"pm_kisan": "farmer income support", "pds": "ration"}
    )

    assert result == "pm_kisan"


async def test_classify_scheme_returns_none_when_not_confident():
    provider = FakeDecisionProvider(
        ChoiceAnswer(choice="pm_kisan", confidence=0.1, probabilities={"pm_kisan": 0.3, "pds": 0.3})
    )

    result = await classify_scheme(provider, "I need help", {"pm_kisan": "farmer income support", "pds": "ration"})

    assert result is None


async def test_classify_scheme_uses_scheme_descriptions_as_criteria():
    provider = FakeDecisionProvider(ChoiceAnswer(choice="pds", confidence=0.9, probabilities={"pds": 0.9}))
    descriptions = {"pm_kisan": "farmer income support", "pds": "ration shop entitlement"}

    await classify_scheme(provider, "I want ration", descriptions)

    assert provider.last_questions["scheme"].criteria == descriptions


async def test_classify_requested_scheme_returns_scheme_id_when_confident():
    provider = FakeDecisionProvider(ChoiceAnswer(choice="pm_kisan", confidence=0.8, probabilities={}))

    result = await classify_requested_scheme(
        provider, "no, tell me about PM-KISAN instead", {"pm_kisan": "farmer income support", "pds": "ration"},
        pinned_scheme_id="pds",
    )

    assert result == ("pm_kisan", True)


async def test_classify_requested_scheme_returns_not_a_switch_when_not_switching():
    # The explicit "not_switching" option exists so a plain fact statement ("I'm 45") doesn't get
    # forced into one of the real scheme choices — decide() always returns a top choice among
    # whatever options it's given.
    provider = FakeDecisionProvider(ChoiceAnswer(choice="not_switching", confidence=0.95, probabilities={}))

    result = await classify_requested_scheme(
        provider, "I'm 45", {"pm_kisan": "farmer income support", "pds": "ration"}, pinned_scheme_id="pds"
    )

    assert result == (None, False)


async def test_classify_requested_scheme_returns_unresolved_switch_when_switching_unspecified():
    # "no, not this one" — wants to leave the current scheme but named no replacement. Distinct
    # from not_switching: this IS a switch attempt, just an unresolved one, so callers (e.g. the
    # orchestrator) know to ask "which scheme?" rather than treating it like a fact statement.
    provider = FakeDecisionProvider(ChoiceAnswer(choice="switching_unspecified", confidence=0.9, probabilities={}))

    result = await classify_requested_scheme(
        provider, "no, not this one", {"pm_kisan": "farmer income support", "pds": "ration"}, pinned_scheme_id="pds"
    )

    assert result == (None, True)


async def test_classify_requested_scheme_treats_low_confidence_real_choice_as_unresolved_switch():
    # A real scheme was the top choice, just not confidently — still a switch attempt (unlike
    # not_switching), so is_switch_attempt must stay True even though scheme_id comes back None.
    provider = FakeDecisionProvider(ChoiceAnswer(choice="pm_kisan", confidence=0.1, probabilities={}))

    result = await classify_requested_scheme(
        provider, "hmm", {"pm_kisan": "farmer income support", "pds": "ration"}, pinned_scheme_id="pds"
    )

    assert result == (None, True)


async def test_classify_requested_scheme_excludes_pinned_scheme_and_includes_meta_options():
    provider = FakeDecisionProvider(ChoiceAnswer(choice="not_switching", confidence=0.9, probabilities={}))
    descriptions = {"pm_kisan": "farmer income support", "pds": "ration shop entitlement"}

    await classify_requested_scheme(provider, "I want ration", descriptions, pinned_scheme_id="pds")

    criteria = provider.last_questions["requested_scheme"].criteria
    assert "pds" not in criteria
    assert "pm_kisan" in criteria
    assert "not_switching" in criteria
    assert "switching_unspecified" in criteria
