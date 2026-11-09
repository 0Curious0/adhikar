import { useCallback, useEffect, useRef, useState } from 'react'
import { ttsStreamUrl } from '../api'
import type { LanguageCode } from '../types'

const SAMPLE_RATE = 48000 // matches AudioConfig(container="raw")'s default in adhikar.api.tts_stream

// One /tts/stream WebSocket is opened lazily and reused across replies for as long as
// languageCode stays the same, mirroring the relay's own reuse of one TTSStream.events()
// iterator across multiple texts sent over one connection (adhikar.api.tts_stream).
export function useReplyPlayback(languageCode: LanguageCode) {
  const wsRef = useRef<WebSocket | null>(null)
  const playCtxRef = useRef<AudioContext | null>(null)
  const nextPlayTimeRef = useRef(0)
  const [error, setError] = useState<string | null>(null)

  const closeSocket = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  useEffect(() => closeSocket, [languageCode, closeSocket])

  const playChunk = useCallback((buffer: ArrayBuffer) => {
    if (!playCtxRef.current) {
      playCtxRef.current = new AudioContext({ sampleRate: SAMPLE_RATE })
      nextPlayTimeRef.current = playCtxRef.current.currentTime
    }
    const ctx = playCtxRef.current
    const int16 = new Int16Array(buffer)
    const float32 = new Float32Array(int16.length)
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 0x8000

    const audioBuffer = ctx.createBuffer(1, float32.length, SAMPLE_RATE)
    audioBuffer.copyToChannel(float32, 0)
    const source = ctx.createBufferSource()
    source.buffer = audioBuffer
    source.connect(ctx.destination)

    const startAt = Math.max(nextPlayTimeRef.current, ctx.currentTime)
    source.start(startAt)
    nextPlayTimeRef.current = startAt + audioBuffer.duration
  }, [])

  const ensureSocket = useCallback((): Promise<WebSocket> => {
    const existing = wsRef.current
    if (existing && existing.readyState === WebSocket.OPEN) return Promise.resolve(existing)

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(ttsStreamUrl(languageCode))
      ws.binaryType = 'arraybuffer'
      ws.onopen = () => {
        wsRef.current = ws
        resolve(ws)
      }
      ws.onerror = () => reject(new Error('tts stream connection failed'))
      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          playChunk(event.data)
          return
        }
        // A non-binary message is the relay's explicit error signal (adhikar.api.tts_stream) —
        // Timbre failed mid-synthesis. Without this, a server-side TTS error is silent: the
        // browser sent text and just never receives any audio back, indistinguishable from
        // "still synthesizing."
        try {
          const message = JSON.parse(event.data)
          if (message.type === 'error') setError("Couldn't play the voice reply — try again.")
        } catch {
          // Unexpected text frame shape — nothing useful to do with it.
        }
      }
    })
  }, [languageCode, playChunk])

  const speak = useCallback(
    async (text: string) => {
      setError(null)
      const ws = await ensureSocket()
      ws.send(text)
    },
    [ensureSocket],
  )

  return { speak, error }
}
