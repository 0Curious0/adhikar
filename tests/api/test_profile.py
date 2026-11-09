from httpx import ASGITransport, AsyncClient

from adhikar.api.app import app
from adhikar.api.routes import get_profile_store, get_schemes
from adhikar.dialogue.profile import ProfileStore, UserProfile
from adhikar.schemes import EligibilityRule, Jurisdiction, RuleOperator, SchemeDocument, VerificationStatus

SCHEME = SchemeDocument(
    schema_version="1.0",
    scheme_id="test_scheme",
    jurisdiction=Jurisdiction(level="central", country="IN"),
    name={"en": "Test Scheme", "hi": "परीक्षण योजना"},
    eligibility_rules=[
        EligibilityRule(
            rule_id="r1",
            field="age_years",
            operator=RuleOperator.GREATER_THAN_OR_EQUAL,
            value=18,
            verification_status=VerificationStatus.VERIFIED,
        )
    ],
)


class FakeProfileStore(ProfileStore):
    def __init__(self, profile: UserProfile):
        self._profile = profile

    def get(self, user_id: str) -> UserProfile:
        return self._profile

    def save(self, profile: UserProfile) -> None:
        raise NotImplementedError


async def _get_profile(profile: UserProfile, *, language: str | None = None):
    app.dependency_overrides[get_profile_store] = lambda: FakeProfileStore(profile)
    app.dependency_overrides[get_schemes] = lambda: {"test_scheme": SCHEME}
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            params = {"language": language} if language else {}
            return await client.get("/profile/u1", params=params)
    finally:
        app.dependency_overrides.pop(get_profile_store, None)
        app.dependency_overrides.pop(get_schemes, None)


async def test_profile_with_no_pinned_scheme_has_no_eligibility_status():
    response = await _get_profile(UserProfile(user_id="u1"))

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "u1",
        "pinned_scheme_id": None,
        "scheme_name": None,
        "facts": {},
        "eligibility_status": None,
    }


async def test_profile_computes_eligibility_deterministically_from_facts():
    profile = UserProfile(user_id="u1", facts={"age_years": 25}, pinned_scheme_id="test_scheme")

    response = await _get_profile(profile)

    body = response.json()
    assert body["scheme_name"] == "Test Scheme"
    assert body["eligibility_status"] == "eligible"
    assert body["facts"] == {"age_years": 25}


async def test_profile_reports_missing_fields_when_facts_incomplete():
    profile = UserProfile(user_id="u1", facts={}, pinned_scheme_id="test_scheme")

    response = await _get_profile(profile)

    assert response.json()["eligibility_status"] == "missing_fields"


async def test_profile_returns_localized_scheme_name():
    profile = UserProfile(user_id="u1", facts={"age_years": 25}, pinned_scheme_id="test_scheme")

    response = await _get_profile(profile, language="hi")

    assert response.json()["scheme_name"] == "परीक्षण योजना"
