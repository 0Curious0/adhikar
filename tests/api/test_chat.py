from httpx import ASGITransport, AsyncClient

from adhikar.api.app import app
from adhikar.api.routes import get_orchestrator


class FakeOrchestrator:
    def __init__(self, reply: str | None):
        self._reply = reply
        self.calls: list[dict[str, str]] = []

    async def handle_turn(self, *, user_id: str, transcript: str, language_code: str) -> str | None:
        self.calls.append({"user_id": user_id, "transcript": transcript, "language_code": language_code})
        return self._reply


async def _post_chat(orchestrator: FakeOrchestrator, body: dict[str, str]):
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/chat", json=body)
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)


async def test_chat_returns_orchestrators_reply():
    orchestrator = FakeOrchestrator(reply="You are eligible.")

    response = await _post_chat(
        orchestrator, {"user_id": "u1", "transcript": "am I eligible?", "language_code": "en-IN"}
    )

    assert response.status_code == 200
    assert response.json() == {"reply": "You are eligible."}


async def test_chat_passes_body_fields_through_to_orchestrator():
    orchestrator = FakeOrchestrator(reply="ok")

    await _post_chat(orchestrator, {"user_id": "u1", "transcript": "am I eligible?", "language_code": "hi-IN"})

    assert orchestrator.calls == [{"user_id": "u1", "transcript": "am I eligible?", "language_code": "hi-IN"}]


async def test_chat_returns_null_reply_when_orchestrator_has_nothing_to_say():
    orchestrator = FakeOrchestrator(reply=None)

    response = await _post_chat(orchestrator, {"user_id": "u1", "transcript": "lol random", "language_code": "en-IN"})

    assert response.status_code == 200
    assert response.json() == {"reply": None}


async def test_chat_rejects_missing_fields():
    orchestrator = FakeOrchestrator(reply="ok")

    response = await _post_chat(orchestrator, {"user_id": "u1"})

    assert response.status_code == 422