from httpx import ASGITransport, AsyncClient

from adhikar.api.app import app
from adhikar.api.routes import get_schemes
from adhikar.schemes import Jurisdiction, SchemeDocument

SCHEME = SchemeDocument(
    schema_version="1.0",
    scheme_id="test_scheme",
    jurisdiction=Jurisdiction(level="central", country="IN"),
    name={"en": "Test Scheme", "hi": "परीक्षण योजना"},
    description={"en": "A scheme for testing."},
)


async def _get_schemes(schemes: dict[str, SchemeDocument], *, language: str | None = None):
    app.dependency_overrides[get_schemes] = lambda: schemes
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            params = {"language": language} if language else {}
            return await client.get("/schemes", params=params)
    finally:
        app.dependency_overrides.pop(get_schemes, None)


async def test_schemes_defaults_to_english():
    response = await _get_schemes({"test_scheme": SCHEME})

    assert response.status_code == 200
    assert response.json() == [{"scheme_id": "test_scheme", "name": "Test Scheme", "description": "A scheme for testing."}]


async def test_schemes_returns_localized_name_when_available():
    response = await _get_schemes({"test_scheme": SCHEME}, language="hi")

    assert response.json()[0]["name"] == "परीक्षण योजना"


async def test_schemes_falls_back_to_english_when_language_has_no_translation():
    # The scheme only has an English description — Tamil/Telugu (and any language missing a
    # translation) must fall back rather than return an empty string.
    response = await _get_schemes({"test_scheme": SCHEME}, language="ta")

    assert response.json()[0]["name"] == "Test Scheme"
    assert response.json()[0]["description"] == "A scheme for testing."
