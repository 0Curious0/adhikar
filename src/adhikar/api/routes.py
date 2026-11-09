from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, WebSocket
from pydantic import BaseModel

from ..dialogue import Orchestrator
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


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def get_stt_provider(request: Request) -> STTProvider:
    return request.app.state.stt_provider


def get_tts_provider(request: Request) -> TTSProvider:
    return request.app.state.tts_provider


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
