from unittest.mock import AsyncMock

import pytest

from adhikar.stt.prisma import PrismaSTTStream


async def test_send_audio_forwards_a_correctly_sized_frame():
    ws = AsyncMock()
    stream = PrismaSTTStream(ws)
    frame = b"\x00" * 1024

    await stream.send_audio(frame)

    ws.send.assert_awaited_once_with(frame)


async def test_send_audio_rejects_a_wrong_sized_frame():
    ws = AsyncMock()
    stream = PrismaSTTStream(ws)

    with pytest.raises(ValueError):
        await stream.send_audio(b"\x00" * 500)

    ws.send.assert_not_awaited()
