import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

import httpx
import websockets

from .base import STTProvider, STTStream
from .exceptions import STTRequestError
from .models import OutputStyle, STTStreamEvent, TranscriptResult


class PrismaSTTProvider(STTProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.vachana.ai", timeout: float = 15.0):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def transcribe(
        self,
        audio: bytes,
        *,
        language_code: str,
        output_style: OutputStyle = OutputStyle.VERBATIM,
        filename: str = "audio.wav",
    ) -> TranscriptResult:
        response = await self._client.post(
            f"{self._base_url}/stt/v3",
            headers={"X-API-Key-ID": self._api_key},
            data={"language_code": language_code, "format": output_style.value},
            files={"audio_file": (filename, audio)},
        )
        payload = response.json()

        if not payload.get("success"):
            raise STTRequestError(
                payload.get("error", {}).get("message", "Prisma transcription failed"),
                request_id=payload.get("request_id"),
                status_code=response.status_code,
            )

        output = payload.get("output") or {}
        return TranscriptResult(
            transcript=payload["transcript"],
            literal=output.get("literal", payload["transcript"]),
            language_code=language_code,
            request_id=payload["request_id"],
            truncated=payload.get("truncated", False),
        )

    @asynccontextmanager
    async def stream(
        self,
        *,
        language_code: str,
        sample_rate: int = 16000,
        output_style: OutputStyle = OutputStyle.VERBATIM,
    ) -> AsyncGenerator[STTStream, None]:
        ws_base = self._base_url.replace("http", "ws", 1)
        headers = {
            "x-api-key-id": self._api_key,
            "lang_code": language_code,
            "x-sample-rate": str(sample_rate),
            "x-format": output_style.value,
        }
        async with websockets.connect(f"{ws_base}/stt/v3/stream", additional_headers=headers) as websocket:
            yield PrismaSTTStream(websocket)


class PrismaSTTStream(STTStream):
    FRAME_BYTES = 1024

    def __init__(self, websocket):
        self._ws = websocket

    async def send_audio(self, frame: bytes) -> None:
        if len(frame) != self.FRAME_BYTES:
            raise ValueError(f"expected a {self.FRAME_BYTES}-byte PCM frame, got {len(frame)}")
        await self._ws.send(frame)

    async def events(self) -> AsyncIterator[STTStreamEvent]:
        async for raw_message in self._ws:
            if isinstance(raw_message, bytes):
                continue
            yield STTStreamEvent.from_payload(json.loads(raw_message))

    async def update_settings(self, **settings: object) -> None:
        await self._ws.send(json.dumps({"type": "update_settings", **settings}))
