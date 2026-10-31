from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager

from .models import OutputStyle, STTStreamEvent, TranscriptResult


class STTStream(ABC):
    """An open realtime transcription session for one speaker."""

    @abstractmethod
    async def send_audio(self, frame: bytes) -> None:
        """Send one PCM frame immediately (no internal buffering).

        The caller must supply exactly one correctly-sized, real-time-paced
        frame per call, since Prisma's VAD is sensitive to send timing.
        """

    @abstractmethod
    def events(self) -> AsyncIterator[STTStreamEvent]:
        """Yield transcript/status events as the provider emits them."""

    @abstractmethod
    async def update_settings(self, **settings: object) -> None:
        """Change settings (e.g. language, bias words) for the next speech segment."""


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        *,
        language_code: str,
        output_style: OutputStyle = OutputStyle.VERBATIM,
        filename: str = "audio.wav",
    ) -> TranscriptResult:
        """Transcribe one complete audio clip (REST / WhatsApp path) and return the final result."""

    @abstractmethod
    def stream(
        self,
        *,
        language_code: str,
        sample_rate: int = 16000,
        output_style: OutputStyle = OutputStyle.VERBATIM,
    ) -> AbstractAsyncContextManager[STTStream]:
        """Open a realtime streaming session, used as `async with provider.stream(...) as session`."""
