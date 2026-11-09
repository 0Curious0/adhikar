import { useCallback, useRef, useState } from 'react'
import { sttStreamUrl } from '../api'
import type { LanguageCode, STTStreamMessage } from '../types'

const TARGET_SAMPLE_RATE = 16000

interface DictationSession {
  ws: WebSocket
  audioContext: AudioContext
  workletNode: AudioWorkletNode
  mediaStream: MediaStream
}

// Chat mode's dictation toggle: on, until explicitly toggled off — never silence/VAD-triggered,
// per the project's no-auto-stop rule. One WebSocket per dictation session (opened on start,
// closed on stop), matching the relay's one-shot-per-connection design (adhikar.api.stt_stream).
export function useDictation(languageCode: LanguageCode) {
  const [isDictating, setIsDictating] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  const sessionRef = useRef<DictationSession | null>(null)
  const segmentsRef = useRef<Map<number, string>>(new Map())

  const stop = useCallback(() => {
    const session = sessionRef.current
    if (!session) return
    sessionRef.current = null
    session.workletNode.disconnect()
    session.mediaStream.getTracks().forEach((track) => track.stop())
    void session.audioContext.close()
    if (session.ws.readyState === WebSocket.OPEN) session.ws.close()
    setIsDictating(false)
  }, [])

  const start = useCallback(async () => {
    if (sessionRef.current) return
    segmentsRef.current = new Map()
    setTranscript('')
    setError(null)

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const audioContext = new AudioContext()
      await audioContext.audioWorklet.addModule('/pcm-worklet.js')

      const ws = new WebSocket(sttStreamUrl(languageCode))
      ws.onmessage = (event) => {
        const message: STTStreamMessage = JSON.parse(event.data)
        if (message.type === 'error') {
          setError('Dictation failed — try again.')
          return
        }
        if (message.type !== 'transcript' || message.text === null) return
        if (message.segment_index !== null) {
          segmentsRef.current.set(message.segment_index, message.text)
          const ordered = [...segmentsRef.current.entries()].sort(([a], [b]) => a - b)
          setTranscript(ordered.map(([, text]) => text).join(' '))
        } else {
          setTranscript(message.text)
        }
      }
      ws.onclose = () => stop()

      const sourceNode = audioContext.createMediaStreamSource(mediaStream)
      const workletNode = new AudioWorkletNode(audioContext, 'pcm-downsampler', {
        processorOptions: { inputSampleRate: audioContext.sampleRate, outputSampleRate: TARGET_SAMPLE_RATE },
      })
      workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (ws.readyState === WebSocket.OPEN) ws.send(event.data)
      }
      sourceNode.connect(workletNode)

      sessionRef.current = { ws, audioContext, workletNode, mediaStream }
      setIsDictating(true)
    } catch (err) {
      setError(
        err instanceof DOMException && err.name === 'NotAllowedError'
          ? 'Microphone access was denied — allow it in your browser settings to dictate.'
          : 'Could not start dictation — try again.',
      )
    }
  }, [languageCode, stop])

  return { isDictating, transcript, setTranscript, start, stop, error }
}
