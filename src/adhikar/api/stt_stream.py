import asyncio
from contextlib import suppress

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketDisconnected

from ..stt import STTProvider


async def relay_stt_stream(websocket: WebSocket, *, language_code: str, stt_provider: STTProvider) -> None:
    """Relay one realtime dictation session: client audio frames -> Prisma, Prisma's transcript
    events -> client as JSON. No orchestrator involvement — this is a pure pass-through so the
    browser (which can't hold the Gnani API key itself) can drive a live-updating, editable text
    input. The client alone decides when dictation starts/stops and when to send the result to
    the orchestrator; this relay has no opinion on either."""
    try:
        async with stt_provider.stream(language_code=language_code) as session:

            async def forward_audio() -> None:
                with suppress(WebSocketDisconnect):
                    while True:
                        frame = await websocket.receive_bytes()
                        await session.send_audio(frame)

            async def forward_events() -> None:
                async for event in session.events():
                    await websocket.send_json(
                        {
                            "type": event.type.value,
                            "text": event.text,
                            "segment_id": event.segment_id,
                            "segment_index": event.segment_index,
                        }
                    )

            forward_audio_task = asyncio.create_task(forward_audio())
            forward_events_task = asyncio.create_task(forward_events())
            try:
                done, _ = await asyncio.wait(
                    {forward_audio_task, forward_events_task}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    task.result()
            finally:
                forward_audio_task.cancel()
                forward_events_task.cancel()
                await asyncio.gather(forward_audio_task, forward_events_task, return_exceptions=True)
    finally:
        # Send a clean close frame whenever we end the session ourselves (e.g. Prisma's stream
        # closed/errored) — without this, returning here leaves uvicorn to just drop the raw TCP
        # transport, which the browser sees as an abnormal closure (code 1006) instead of a clean
        # one. Suppressed if the client already disconnected first (closing twice would raise).
        with suppress(WebSocketDisconnect, WebSocketDisconnected):
            await websocket.close()