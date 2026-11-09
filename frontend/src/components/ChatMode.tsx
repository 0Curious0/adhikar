import { AlertCircle, Mic, Square } from 'lucide-react'
import { useEffect, useState } from 'react'
import { postChat } from '../api'
import { useDictation } from '../hooks/useDictation'
import { useReplyPlayback } from '../hooks/useReplyPlayback'
import { useStrings } from '../i18n'
import type { LanguageCode } from '../types'

export function ChatMode(props: {
  userId: string
  languageCode: LanguageCode
  initialText?: string
  onExchange: (transcript: string, reply: string | null) => void
  onCaseChanged: () => void
}) {
  const strings = useStrings(props.languageCode)
  const dictation = useDictation(props.languageCode)
  const { speak, error: playbackError } = useReplyPlayback(props.languageCode)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)

  useEffect(() => {
    if (props.initialText) dictation.setTranscript(props.initialText)
    // Only seed from a new initialText value — the textarea stays freely user-editable afterward.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.initialText])

  function toggleDictation() {
    if (dictation.isDictating) {
      dictation.stop()
    } else {
      void dictation.start()
    }
  }

  async function handleSend() {
    const transcript = dictation.transcript.trim()
    if (!transcript || sending) return

    if (dictation.isDictating) dictation.stop()
    setSending(true)
    setSendError(null)
    try {
      const { reply } = await postChat({ userId: props.userId, transcript, languageCode: props.languageCode })
      props.onExchange(transcript, reply)
      props.onCaseChanged()
      dictation.setTranscript('')
      if (reply) {
        try {
          await speak(reply)
        } catch {
          // Reply text still shows in the exchange log even if voicing it fails — losing audio
          // playback shouldn't erase an otherwise-successful exchange.
        }
      }
    } catch {
      setSendError('Could not send your message — check your connection and try again.')
    } finally {
      setSending(false)
    }
  }

  const activeError = sendError ?? dictation.error ?? playbackError

  return (
    <div className="chat-mode">
      <textarea
        className="chat-mode__input"
        value={dictation.transcript}
        onChange={(event) => dictation.setTranscript(event.target.value)}
        placeholder={strings.chatPlaceholder}
        rows={3}
      />
      {sending && <p className="chat-mode__status">{strings.thinking}</p>}

      {activeError && (
        <p className="chat-mode__error" role="alert">
          <AlertCircle size={14} aria-hidden="true" />
          {activeError}
        </p>
      )}
      <div className="chat-mode__actions">
        <button
          type="button"
          className={`btn btn--secondary${dictation.isDictating ? ' btn--active' : ''}`}
          onClick={toggleDictation}
        >
          {dictation.isDictating ? (
            <Square size={16} aria-hidden="true" />
          ) : (
            <Mic size={16} aria-hidden="true" />
          )}
          <span>{dictation.isDictating ? strings.stopDictation : strings.dictate}</span>
        </button>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => void handleSend()}
          disabled={sending || !dictation.transcript.trim()}
        >
          {sending ? strings.sending : strings.send}
        </button>
      </div>
    </div>
  )
}
