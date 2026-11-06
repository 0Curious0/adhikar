import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

import httpx
import websockets

from .base import TTSProvider, TTSStream
from .exceptions import TTSRequestError
from .models import AudioConfig, TTSStreamEvent


class TimbreTTSProvider(TTSProvider):
    MODEL = "timbre-v2.5"

    def __init__(self, api_key: str, base_url: str = "https://api.vachana.ai", timeout: float = 15.0):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def synthesize(
        self,
        text: str,
        *,
        language_code: str,
        voice: str,
        speed: float | str = 1.0,
        audio_config: AudioConfig = AudioConfig(),
    ) -> bytes:
        response = await self._client.post(
            f"{self._base_url}/api/v1/tts/inference",
            headers={"X-API-Key-ID": self._api_key},
            json={
                "text": text,
                "voice": voice,
                "model": self.MODEL,
                "language": language_code,
                "speed": speed,
                "audio_config": audio_config.model_dump(),
            },
        )

        if response.status_code == 200:
            return response.content

        payload = response.json()
        detail = payload.get("detail")
        if isinstance(detail, dict):
            raise TTSRequestError(
                detail.get("message", "Timbre synthesis failed"),
                status_code=detail.get("status_code", response.status_code),
            )
        raise TTSRequestError(
            payload.get("message", "Timbre synthesis failed"),
            status_code=payload.get("status_code", response.status_code),
        )

    @asynccontextmanager
    async def stream(
        self,
        *,
        language_code: str,
        voice: str,
        speed: float | str = 1.0,
        audio_config: AudioConfig = AudioConfig(),
    ) -> AsyncGenerator[TTSStream, None]:
        ws_base = self._base_url.replace("http", "ws", 1)
        headers = {"x-api-key-id": self._api_key}
        async with websockets.connect(f"{ws_base}/api/v1/tts", additional_headers=headers) as websocket:
            yield TimbreTTSStream(
                websocket,
                language_code=language_code,
                voice=voice,
                speed=speed,
                audio_config=audio_config,
            )


class TimbreTTSStream(TTSStream):
    def __init__(self, websocket, *, language_code: str, voice: str, speed: float | str, audio_config: AudioConfig):
        self._ws = websocket
        self._language_code = language_code
        self._voice = voice
        self._speed = speed
        self._audio_config = audio_config

    async def send_text(self, text: str) -> None:
        await self._ws.send(
            json.dumps(
                {
                    "text": text,
                    "voice": self._voice,
                    "model": TimbreTTSProvider.MODEL,
                    "language": self._language_code,
                    "speed": self._speed,
                    "audio_config": self._audio_config.model_dump(),
                }
            )
        )

    async def events(self) -> AsyncIterator[TTSStreamEvent]:
        async for raw_message in self._ws:
            if isinstance(raw_message, bytes):
                continue
            yield TTSStreamEvent.from_payload(json.loads(raw_message))
