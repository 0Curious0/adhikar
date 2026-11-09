from httpx import ASGITransport, AsyncClient

from adhikar.api.app import app
from adhikar.api.routes import get_activity_log, get_schemes
from adhikar.dialogue.activity import ActivityEntry, ActivityLogStore
from adhikar.schemes import Jurisdiction, SchemeDocument

SCHEME = SchemeDocument(
    schema_version="1.0",
    scheme_id="test_scheme",
    jurisdiction=Jurisdiction(level="central", country="IN"),
    name={"en": "Test Scheme", "hi": "परीक्षण योजना"},
)


class FakeActivityLogStore(ActivityLogStore):
    def __init__(self, entries: list[ActivityEntry]):
        self._entries = entries

    def log(self, user_id: str, *, scheme_id: str, eligibility_status: str) -> None:
        raise NotImplementedError

    def recent(self, user_id: str, *, limit: int = 10) -> list[ActivityEntry]:
        return self._entries[:limit]


async def _get_activity(entries: list[ActivityEntry], *, language: str | None = None, limit: int | None = None):
    app.dependency_overrides[get_activity_log] = lambda: FakeActivityLogStore(entries)
    app.dependency_overrides[get_schemes] = lambda: {"test_scheme": SCHEME}
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            params = {}
            if language:
                params["language"] = language
            if limit is not None:
                params["limit"] = limit
            return await client.get("/activity/u1", params=params)
    finally:
        app.dependency_overrides.pop(get_activity_log, None)
        app.dependency_overrides.pop(get_schemes, None)


async def test_activity_returns_empty_list_when_nothing_logged():
    response = await _get_activity([])

    assert response.status_code == 200
    assert response.json() == []


async def test_activity_resolves_scheme_name_and_passes_through_status():
    entry = ActivityEntry(scheme_id="test_scheme", eligibility_status="eligible", created_at="2026-01-01T00:00:00+00:00")

    response = await _get_activity([entry])

    assert response.json() == [
        {
            "scheme_id": "test_scheme",
            "scheme_name": "Test Scheme",
            "eligibility_status": "eligible",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    ]


async def test_activity_returns_localized_scheme_name():
    entry = ActivityEntry(scheme_id="test_scheme", eligibility_status="eligible", created_at="2026-01-01T00:00:00+00:00")

    response = await _get_activity([entry], language="hi")

    assert response.json()[0]["scheme_name"] == "परीक्षण योजना"


async def test_activity_falls_back_to_scheme_id_when_scheme_no_longer_loaded():
    entry = ActivityEntry(scheme_id="deleted_scheme", eligibility_status="eligible", created_at="2026-01-01T00:00:00+00:00")

    response = await _get_activity([entry])

    assert response.json()[0]["scheme_name"] == "deleted_scheme"


async def test_activity_passes_limit_through_to_store():
    entries = [
        ActivityEntry(scheme_id="test_scheme", eligibility_status="eligible", created_at=f"2026-01-0{i}T00:00:00+00:00")
        for i in range(1, 4)
    ]

    response = await _get_activity(entries, limit=2)

    assert len(response.json()) == 2
