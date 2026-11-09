// The 10 languages Sarvam and Gnani both support — Sarvam also has Odia, but Gnani's STT/TTS
// doesn't, so it's left out to keep the voice pipeline working end-to-end in every language
// offered here (see adhikar.nlg.provider._LANGUAGE_NAMES on the backend).
export type LanguageCode =
  | 'hi-IN'
  | 'en-IN'
  | 'bn-IN'
  | 'gu-IN'
  | 'kn-IN'
  | 'ml-IN'
  | 'mr-IN'
  | 'pa-IN'
  | 'ta-IN'
  | 'te-IN'

export interface ChatResponse {
  reply: string | null
}

export interface SchemeSummary {
  scheme_id: string
  name: string
  description: string
}

export type EligibilityStatus = 'eligible' | 'not_eligible' | 'missing_fields'

export interface CaseResponse {
  user_id: string
  pinned_scheme_id: string | null
  scheme_name: string | null
  facts: Record<string, unknown>
  eligibility_status: EligibilityStatus | null
}

export interface ActivityItem {
  scheme_id: string
  scheme_name: string
  eligibility_status: EligibilityStatus
  created_at: string
}

// Mirrors stt_stream.py's forwarded event shape exactly (a subset of STTStreamEvent's fields —
// the relay only forwards type/text/segment_id/segment_index, not audio_duration_ms/latency_ms).
export type STTEventType =
  | 'connected'
  | 'speech_start'
  | 'processing'
  | 'transcript'
  | 'settings_updated'
  | 'error'

export interface STTStreamMessage {
  type: STTEventType
  text: string | null
  segment_id: string | null
  segment_index: number | null
}

export interface Exchange {
  id: string
  transcript: string
  reply: string | null
}
