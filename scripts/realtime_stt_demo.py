"""Manual test tool: speak into the mic, see live Prisma transcripts.

Usage: uv run python scripts/realtime_stt_demo.py [language_code]
"""

import asyncio
import sys

import sounddevice as sd

from adhikar.config import get_settings
from adhikar.stt import PrismaSTTProvider, STTEventType

SAMPLE_RATE = 16000
FRAME_SAMPLES = 512  # 512 samples * 2 bytes (int16) = 1024 bytes, Prisma's required frame size


async def main(language_code: str) -> None:
    settings = get_settings()
    provider = PrismaSTTProvider(api_key=settings.gnani_api_key, base_url=settings.prisma_base_url)

    # to get the asyncio event loop from the callback thread as sounddevice uses a separate thread for the callback
    loop = asyncio.get_running_loop()
    # create an async io queue to hold audio frames from the mic callback, with type safety for bytes
    frames: asyncio.Queue[bytes] = asyncio.Queue()

    def on_audio_block(indata, _frame_count, _time_info, status):
        if status:
            print(f"! mic status: {status}", file=sys.stderr)
        loop.call_soon_threadsafe(frames.put_nowait, bytes(indata))

    async with provider.stream(language_code=language_code, sample_rate=SAMPLE_RATE) as session:

        async def print_events() -> None:
            async for event in session.events():
                if event.type == STTEventType.TRANSCRIPT:
                    print(f"> {event.text}")
                elif event.type == STTEventType.ERROR:
                    print(f"! error: {event.raw.get('message')}", file=sys.stderr)

        consumer = asyncio.create_task(print_events())

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            callback=on_audio_block,
        ):
            print(f"Listening ({language_code})... Ctrl+C to stop.")
            try:
                while True:
                    frame = await frames.get()
                    await session.send_audio(frame)
            except KeyboardInterrupt:
                pass

        consumer.cancel()

    await provider.aclose()


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "en-IN"
    asyncio.run(main(lang))
