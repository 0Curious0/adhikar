import { Mic } from 'lucide-react'
import { useRef, useState } from 'react'
import { postVoice } from '../api'
import { useStrings, type Strings } from '../i18n'
import type { LanguageCode } from '../types'

type Status = 'idle' | 'recording' | 'thinking' | 'playing' | 'no_reply' | 'error'

function statusLabel(strings: Strings, status: Status): string {
  return {
    idle: strings.tapToSpeak,
    recording: strings.listening,
    thinking: strings.thinking,
    playing: strings.speaking,
    no_reply: strings.noReply,
    error: strings.error,
  }[status]
}

// Push-to-talk, never silence/VAD-based auto-stop: the user explicitly starts and stops one
// complete clip, which is then sent as a single /voice request (transcribe -> orchestrator ->
// synthesize happens server-side). No transcript is shown here, deliberately — reading/editing
// a transcript would reintroduce the literacy barrier voice mode exists to route around.
export function VoiceMode(props: { userId: string; languageCode: LanguageCode; onCaseChanged: () => void }) {
  const strings = useStrings(props.languageCode)
  const [status, setStatus] = useState<Status>('idle')
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        void sendClip(new Blob(chunksRef.current, { type: recorder.mimeType }))
      }
      recorder.start()
      mediaRecorderRef.current = recorder
      setStatus('recording')
    } catch {
      setStatus('error')
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop()
    setStatus('thinking')
  }

  async function sendClip(audio: Blob) {
    try {
      const reply = await postVoice({ userId: props.userId, languageCode: props.languageCode, audio })
      props.onCaseChanged()
      if (reply === null) {
        setStatus('no_reply')
        return
      }
      const url = URL.createObjectURL(reply)
      if (audioRef.current) {
        audioRef.current.src = url
        await audioRef.current.play()
      }
      setStatus('playing')
    } catch {
      setStatus('error')
    }
  }

  function handleTap() {
    if (status === 'recording') {
      stopRecording()
    } else if (status === 'idle' || status === 'no_reply' || status === 'error') {
      void startRecording()
    }
  }

  const disabled = status === 'thinking' || status === 'playing'

  return (
    <div className="voice-mode">
      <button
        type="button"
        className={`mic-btn${status === 'recording' ? ' mic-btn--active' : ''}`}
        onClick={handleTap}
        disabled={disabled}
        aria-label="Push to talk"
      >
        <Mic size={32} aria-hidden="true" />
      </button>
      <p className="voice-mode__status">{statusLabel(strings, status)}</p>
      <audio ref={audioRef} onEnded={() => setStatus('idle')} hidden />
    </div>
  )
}
