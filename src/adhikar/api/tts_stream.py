from contextlib import suppress

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketDisconnected

from ..tts import AudioConfig, TTSEventType, TTSProvider

# Timbre v2.5 voices aren't language-scoped (unlike v3.0's), so one hardcoded voice covers all
# 10 MVP languages — not a per-call knob, mirrors TimbreTTSProvider.MODEL being pinned.
DEFAULT_VOICE = "Nalini"


async def relay_tts_stream(websocket: WebSocket, *, language_code: str, tts_provider: TTSProvider) -> None:
    """Relay realtime reply-voicing: client sends one reply's text, server streams back Timbre's
    audio chunks for it. No orchestrator involvement — purely a pass-through so the browser (which
    can't hold the Gnani API key itself) can play a reply as it's synthesized. The same session is
    reused across multiple texts sent over one connection (one per chat-mode reply), since each
    `send_text()` call's events are just the next `audio...complete` run on the same stream."""
    try:
        async with tts_provider.stream(
            language_code=language_code, voice=DEFAULT_VOICE, audio_config=AudioConfig(container="raw")
        ) as session:
            events = session.events()
            with suppress(WebSocketDisconnect):
                while True:
                    text = await websocket.receive_text()
                    await session.send_text(text)
                    async for event in events:
                        if event.type == TTSEventType.AUDIO and event.audio:
                            await websocket.send_bytes(event.audio)
                        elif event.type in (TTSEventType.COMPLETE, TTSEventType.ERROR):
                            break
    finally:
        with suppress(WebSocketDisconnect, WebSocketDisconnected):
            await websocket.close()