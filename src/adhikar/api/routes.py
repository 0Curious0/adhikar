from typing import Any

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, WebSocket
from pydantic import BaseModel

from ..dialogue import Orchestrator
from ..dialogue.activity import ActivityLogStore
from ..dialogue.profile import ProfileStore
from ..schemes import SchemeDocument, evaluate
from ..stt import STTProvider
from ..tts import TTSProvider
from .stt_stream import relay_stt_stream
from .tts_stream import DEFAULT_VOICE, relay_tts_stream

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    transcript: str
    language_code: str


class ChatResponse(BaseModel):
    reply: str | None


class SchemeSummary(BaseModel):
    scheme_id: str
    name: str
    description: str


class CaseResponse(BaseModel):
    user_id: str
    pinned_scheme_id: str | None
    scheme_name: str | None
    facts: dict[str, Any]
    eligibility_status: str | None


class ActivityItem(BaseModel):
    scheme_id: str
    scheme_name: str
    eligibility_status: str
    created_at: str


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def get_stt_provider(request: Request) -> STTProvider:
    return request.app.state.stt_provider


def get_tts_provider(request: Request) -> TTSProvider:
    return request.app.state.tts_provider


def get_profile_store(request: Request) -> ProfileStore:
    return request.app.state.profile_store


def get_activity_log(request: Request) -> ActivityLogStore:
    return request.app.state.activity_log


def get_schemes(request: Request) -> dict[str, SchemeDocument]:
    return request.app.state.schemes


def get_stt_provider_ws(websocket: WebSocket) -> STTProvider:
    return websocket.app.state.stt_provider


def get_tts_provider_ws(websocket: WebSocket) -> TTSProvider:
    return websocket.app.state.tts_provider


@router.post("/chat")
async def chat(body: ChatRequest, orchestrator: Orchestrator = Depends(get_orchestrator)) -> ChatResponse:
    reply = await orchestrator.handle_turn(
        user_id=body.user_id, transcript=body.transcript, language_code=body.language_code
    )
    return ChatResponse(reply=reply)


def _localized_name(doc: SchemeDocument, language: str) -> str:
    return doc.name.get(language) or doc.name.get("en", doc.scheme_id)


def _localized_description(doc: SchemeDocument, language: str) -> str:
    return doc.description.get(language) or doc.description.get("en", "")


@router.get("/schemes")
async def list_schemes(
    language: str = "en", schemes: dict[str, SchemeDocument] = Depends(get_schemes)
) -> list[SchemeSummary]:
    # Scheme files only ever carry `en`/`hi` name/description text (see adhikar.schemes.models) —
    # Tamil/Telugu intentionally fall back to English here rather than being blank, since no
    # Tamil/Telugu scheme text exists or is meant to.
    return [
        SchemeSummary(scheme_id=scheme_id, name=_localized_name(doc, language), description=_localized_description(doc, language))
        for scheme_id, doc in schemes.items()
    ]


@router.get("/profile/{user_id}")
async def get_profile(
    user_id: str,
    language: str = "en",
    profile_store: ProfileStore = Depends(get_profile_store),
    schemes: dict[str, SchemeDocument] = Depends(get_schemes),
) -> CaseResponse:
    profile = profile_store.get(user_id)
    scheme_name = None
    eligibility_status = None
    if profile.pinned_scheme_id is not None:
        doc = schemes[profile.pinned_scheme_id]
        scheme_name = _localized_name(doc, language)
        eligibility_status = evaluate(doc, profile.facts).status.value

    return CaseResponse(
        user_id=user_id,
        pinned_scheme_id=profile.pinned_scheme_id,
        scheme_name=scheme_name,
        facts=profile.facts,
        eligibility_status=eligibility_status,
    )


@router.get("/activity/{user_id}")
async def get_activity(
    user_id: str,
    language: str = "en",
    limit: int = 10,
    activity_log: ActivityLogStore = Depends(get_activity_log),
    schemes: dict[str, SchemeDocument] = Depends(get_schemes),
) -> list[ActivityItem]:
    entries = activity_log.recent(user_id, limit=limit)
    items = []
    for entry in entries:
        doc = schemes.get(entry.scheme_id)
        scheme_name = _localized_name(doc, language) if doc is not None else entry.scheme_id
        items.append(
            ActivityItem(
                scheme_id=entry.scheme_id,
                scheme_name=scheme_name,
                eligibility_status=entry.eligibility_status,
                created_at=entry.created_at,
            )
        )
    return items


@router.post("/voice")
async def voice(
    user_id: str = Form(),
    language_code: str = Form(),
    audio: UploadFile = File(),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    stt_provider: STTProvider = Depends(get_stt_provider),
    tts_provider: TTSProvider = Depends(get_tts_provider),
) -> Response:
    transcription = await stt_provider.transcribe(
        await audio.read(), language_code=language_code, filename=audio.filename or "audio.wav"
    )

    reply = await orchestrator.handle_turn(
        user_id=user_id, transcript=transcription.transcript, language_code=language_code
    )
    if reply is None:
        return Response(status_code=204)

    audio_reply = await tts_provider.synthesize(reply, language_code=language_code, voice=DEFAULT_VOICE)
    return Response(content=audio_reply, media_type="audio/wav")


@router.websocket("/stt/stream")
async def stt_stream(
    websocket: WebSocket, language_code: str, stt_provider: STTProvider = Depends(get_stt_provider_ws)
) -> None:
    await websocket.accept()
    await relay_stt_stream(websocket, language_code=language_code, stt_provider=stt_provider)


@router.websocket("/tts/stream")
async def tts_stream(
    websocket: WebSocket, language_code: str, tts_provider: TTSProvider = Depends(get_tts_provider_ws)
) -> None:
    await websocket.accept()
    await relay_tts_stream(websocket, language_code=language_code, tts_provider=tts_provider)
