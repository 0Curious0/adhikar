"""Manual test tool: synthesize text with Timbre and play it back.

Usage: uv run python scripts/tts_demo.py ["<text>" [language_code] [voice]] [--stream]
"""

import asyncio
import io
import sys
import wave

import numpy as np
import sounddevice as sd

from adhikar.config import get_settings
from adhikar.tts import AudioConfig, TimbreTTSProvider, TTSEventType

OUTPUT_PATH = "tts_output.wav"


def play_wav(wav_bytes: bytes) -> None:
    with wave.open(io.BytesIO(wav_bytes)) as wav_file:
        frames = wav_file.readframes(wav_file.getnframes())
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()

    audio = np.frombuffer(frames, dtype=np.int16).reshape(-1, channels)
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


async def synthesize_rest(provider: TimbreTTSProvider, text: str, language_code: str, voice: str) -> bytes:
    return await provider.synthesize(text, language_code=language_code, voice=voice)


async def synthesize_stream(provider: TimbreTTSProvider, text: str, language_code: str, voice: str) -> None:
    """Play each audio chunk as it arrives, for real low-latency playback. Nothing is saved to disk."""
    audio_config = AudioConfig(container="raw")

    with sd.RawOutputStream(
        samplerate=audio_config.sample_rate,
        channels=audio_config.num_channels,
        dtype="int16",
    ) as output_stream:
        async with provider.stream(language_code=language_code, voice=voice, audio_config=audio_config) as session:
            await session.send_text(text)
            async for event in session.events():
                if event.type == TTSEventType.AUDIO and event.audio:
                    output_stream.write(event.audio)
                elif event.type == TTSEventType.COMPLETE:
                    break
                elif event.type == TTSEventType.ERROR:
                    print(f"! error: {event.message}", file=sys.stderr)
                    break


async def main(text: str, language_code: str, voice: str, use_stream: bool) -> None:
    settings = get_settings()
    provider = TimbreTTSProvider(api_key=settings.gnani_api_key, base_url=settings.gnani_base_url)

    mode = "streaming" if use_stream else "REST"
    print(f"Synthesizing ({mode}, {language_code}, voice={voice})...")

    if use_stream:
        audio_bytes = await synthesize_stream(provider, text, language_code, voice)
        await provider.aclose()
    else:
        audio_bytes = await synthesize_rest(provider, text, language_code, voice)
        await provider.aclose()

        with open(OUTPUT_PATH, "wb") as f:
            f.write(audio_bytes)
        print(f"Wrote {len(audio_bytes)} bytes to {OUTPUT_PATH}")

        play_wav(audio_bytes)


if __name__ == "__main__":
    use_stream = "--stream" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--stream"]

    text = args[0] if len(args) > 0 else "नमस्ते, आप कैसे हैं?"
    language_code = args[1] if len(args) > 1 else "hi-IN"
    voice = args[2] if len(args) > 2 else "Nalini"

    asyncio.run(main(text, language_code, voice, use_stream))
