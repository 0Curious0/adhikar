from enum import Enum

from pydantic import BaseModel, ConfigDict


class OutputStyle(str, Enum):
    VERBATIM = "verbatim"
    TRANSCRIBE = "transcribe"


class TranscriptResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    transcript: str
    literal: str
    language_code: str
    request_id: str
    truncated: bool = False


class STTEventType(str, Enum):
    CONNECTED = "connected"
    SPEECH_START = "speech_start"
    PROCESSING = "processing"
    TRANSCRIPT = "transcript"
    SETTINGS_UPDATED = "settings_updated"
    ERROR = "error"


class STTStreamEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: STTEventType
    raw: dict
    text: str | None = None
    segment_id: str | None = None
    segment_index: int | None = None
    audio_duration_ms: int | None = None
    latency_ms: int | None = None

    @classmethod
    def from_payload(cls, payload: dict) -> "STTStreamEvent":
        return cls(
            type=payload["type"],
            raw=payload,
            text=payload.get("text"),
            segment_id=payload.get("segment_id"),
            segment_index=payload.get("segment_index"),
            audio_duration_ms=payload.get("audio_duration_ms"),
            latency_ms=payload.get("latency"),              # renaming latency attribute in payload to latency_ms in the model, thats why creating a from_payload class method to handle this mapping instead of **payload
        )
