from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager

from .models import AudioConfig, TTSStreamEvent


class TTSStream(ABC):
    """An open realtime synthesis session."""

    @abstractmethod
    async def send_text(self, text: str) -> None:
        """Send one complete synthesis request for this text over the open connection.

        The server streams back audio events for this request and ends with a
        `complete` event; another `send_text()` call may follow on the same session.
        """

    @abstractmethod
    def events(self) -> AsyncIterator[TTSStreamEvent]:
        """Yield audio/status events as the provider emits them."""


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        *,
        language_code: str,
        voice: str,
        speed: float | str = 1.0,
        audio_config: AudioConfig = AudioConfig(),
    ) -> bytes:
        """Synthesize one complete block of text (REST / WhatsApp path) and return the audio."""

    @abstractmethod
    def stream(
        self,
        *,
        language_code: str,
        voice: str,
        speed: float | str = 1.0,
        audio_config: AudioConfig = AudioConfig(),
    ) -> AbstractAsyncContextManager[TTSStream]:
        """Open a realtime synthesis session, used as `async with provider.stream(...) as session`."""