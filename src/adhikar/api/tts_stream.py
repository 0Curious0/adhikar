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
    can't hold the Gnani API key itself) can play a reply as it's synthesized.

    A fresh upstream Timbre connection is opened per text, not one held open and reused across every
    reply in the session — only the browser<->backend connection stays open for the session's
    lifetime. Reuse was tried first and empirically does not hold up: on one connection, sequential
    `send_text()` calls silently dropped every other reply (0 audio bytes, a differently-shaped
    `complete` event carrying no `data`, and the exact same stale `request_id` repeated across every
    dropped reply), even with a deliberate delay between sends — a fresh connection per send was
    100% reliable across the same test. Timbre's realtime endpoint is built for one input producing
    one streamed output per connection, not multiple sequential inputs on one connection."""
    try:
        with suppress(WebSocketDisconnect):
            while True:
                text = await websocket.receive_text()
                async with tts_provider.stream(
                    language_code=language_code, voice=DEFAULT_VOICE, audio_config=AudioConfig(container="raw")
                ) as session:
                    await session.send_text(text)
                    async for event in session.events():
                        if event.type == TTSEventType.AUDIO and event.audio:
                            await websocket.send_bytes(event.audio)
                        elif event.type == TTSEventType.ERROR:
                            # Unlike COMPLETE, this needs an explicit signal to the client — with
                            # no message at all, the browser just sent text and gets silence back,
                            # indistinguishable from "still synthesizing." A JSON text frame is safe
                            # alongside the binary AUDIO frames on this connection (the client tells
                            # them apart by type, same as stt_stream.py's relay already does).
                            await websocket.send_json({"type": "error", "message": event.message})
                            break
                        elif event.type == TTSEventType.COMPLETE:
                            break
    finally:
        with suppress(WebSocketDisconnect, WebSocketDisconnected):
            await websocket.close()