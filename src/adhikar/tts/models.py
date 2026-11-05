import base64
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AudioConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_rate: int = 48000
    num_channels: int = 1
    sample_width: int = 2
    encoding: str = "linear_pcm"
    container: str = "wav"


class TTSEventType(str, Enum):
    START = "start"
    AUDIO = "audio"
    COMPLETE = "complete"
    ERROR = "error"


class TTSStreamEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: TTSEventType
    raw: dict
    request_id: str | None = None
    chunk_index: int | None = None
    audio: bytes | None = None
    is_final: bool | None = None
    message: str | None = None

    @classmethod
    def from_payload(cls, payload: dict) -> "TTSStreamEvent":
        data = payload.get("data") or {}
        audio_b64 = data.get("audio")
        return cls(
            type=payload["type"],
            raw=payload,
            request_id=payload.get("request_id"),
            chunk_index=data.get("chunk_index"),
            audio=base64.b64decode(audio_b64) if audio_b64 else None,
            is_final=data.get("is_final"),
            message=payload.get("message"),
        )
