import type { ActivityItem, CaseResponse, ChatResponse, LanguageCode, SchemeSummary } from './types'

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const WS_BASE = API_BASE.replace(/^http/, 'ws')

export async function postChat(params: {
  userId: string
  transcript: string
  languageCode: LanguageCode
}): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: params.userId,
      transcript: params.transcript,
      language_code: params.languageCode,
    }),
  })
  if (!response.ok) throw new Error(`/chat failed: ${response.status}`)
  return response.json()
}

// Returns null for a 204 (orchestrator had nothing to say) — the caller distinguishes
// "no reply" from "got an audio reply" the same way the backend route does.
export async function postVoice(params: {
  userId: string
  languageCode: LanguageCode
  audio: Blob
}): Promise<Blob | null> {
  const extension = params.audio.type.split('/')[1]?.split(';')[0] || 'webm'
  const body = new FormData()
  body.append('user_id', params.userId)
  body.append('language_code', params.languageCode)
  body.append('audio', params.audio, `clip.${extension}`)

  const response = await fetch(`${API_BASE}/voice`, { method: 'POST', body })
  if (response.status === 204) return null
  if (!response.ok) throw new Error(`/voice failed: ${response.status}`)
  return response.blob()
}

// Scheme JSON only ever carries `en`/`hi` text (see adhikar.schemes.models), so only the 2-letter
// language prefix is sent — ta-IN/te-IN correctly fall back to English server-side rather than
// pretending Tamil/Telugu scheme text exists.
function languagePrefix(languageCode: LanguageCode): string {
  return languageCode.split('-')[0]
}

export async function getSchemes(languageCode: LanguageCode): Promise<SchemeSummary[]> {
  const response = await fetch(`${API_BASE}/schemes?language=${languagePrefix(languageCode)}`)
  if (!response.ok) throw new Error(`/schemes failed: ${response.status}`)
  return response.json()
}

export async function getProfile(userId: string, languageCode: LanguageCode): Promise<CaseResponse> {
  const response = await fetch(
    `${API_BASE}/profile/${encodeURIComponent(userId)}?language=${languagePrefix(languageCode)}`,
  )
  if (!response.ok) throw new Error(`/profile failed: ${response.status}`)
  return response.json()
}

export async function getActivity(userId: string, languageCode: LanguageCode): Promise<ActivityItem[]> {
  const response = await fetch(
    `${API_BASE}/activity/${encodeURIComponent(userId)}?language=${languagePrefix(languageCode)}`,
  )
  if (!response.ok) throw new Error(`/activity failed: ${response.status}`)
  return response.json()
}

export function sttStreamUrl(languageCode: LanguageCode): string {
  return `${WS_BASE}/stt/stream?language_code=${encodeURIComponent(languageCode)}`
}

export function ttsStreamUrl(languageCode: LanguageCode): string {
  return `${WS_BASE}/tts/stream?language_code=${encodeURIComponent(languageCode)}`
}
