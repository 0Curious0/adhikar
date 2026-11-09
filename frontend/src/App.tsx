import { useEffect, useRef, useState } from 'react'
import './App.css'
import { getActivity, getSchemes } from './api'
import { CasePanel } from './components/CasePanel'
import { ChatMode } from './components/ChatMode'
import { ExchangeLog } from './components/ExchangeLog'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { HowItWorks } from './components/HowItWorks'
import { NeedHelpCard } from './components/NeedHelpCard'
import { SchemeCardsSection } from './components/SchemeCardsSection'
import { VoiceMode } from './components/VoiceMode'
import { useUserId } from './hooks/useUserId'
import type { ActivityItem, Exchange, LanguageCode, SchemeSummary } from './types'

const LANGUAGE_STORAGE_KEY = 'adhikar.language_code'
type Mode = 'voice' | 'chat' | null

export default function App() {
  const userId = useUserId()
  const [languageCode, setLanguageCode] = useState<LanguageCode>(
    () => (localStorage.getItem(LANGUAGE_STORAGE_KEY) as LanguageCode | null) ?? 'en-IN',
  )
  const [mode, setMode] = useState<Mode>(null)
  const [chatSeedText, setChatSeedText] = useState<string | undefined>(undefined)
  const [schemes, setSchemes] = useState<SchemeSummary[]>([])
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [activityLoading, setActivityLoading] = useState(true)
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const interactionPanelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, languageCode)
  }, [languageCode])

  // Scheme names/descriptions and the pinned scheme's name are localized server-side (en/hi —
  // see adhikar.api.routes._localized_name), so both need refetching whenever the UI language
  // changes, not just once on mount.
  useEffect(() => {
    getSchemes(languageCode).then(setSchemes).catch(() => setSchemes([]))
  }, [languageCode])

  const refreshActivity = () => {
    setActivityLoading(true)
    getActivity(userId, languageCode)
      .then(setActivity)
      .catch(() => setActivity([]))
      .finally(() => setActivityLoading(false))
  }

  useEffect(refreshActivity, [userId, languageCode])

  const addExchange = (transcript: string, reply: string | null) => {
    setExchanges((prev) => [...prev, { id: crypto.randomUUID(), transcript, reply }])
  }

  // Scheme cards and activity rows don't have a dedicated detail view in this MVP — opening one
  // means dropping the user straight into Chat mode with a relevant question pre-filled, reusing
  // the real orchestrator/eligibility flow instead of a separate static "details" page.
  function openChatWith(text: string) {
    setMode('chat')
    setChatSeedText(text)
    interactionPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function handleSelectScheme(scheme: SchemeSummary) {
    openChatWith(`Tell me about ${scheme.name} and check if I'm eligible.`)
  }

  function handleSelectActivity(item: ActivityItem) {
    openChatWith(`Continue checking my eligibility for ${item.scheme_name}.`)
  }

  function handleSpeak() {
    setMode('voice')
    interactionPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function handleType() {
    setChatSeedText(undefined)
    setMode('chat')
    interactionPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="app">
      <Header languageCode={languageCode} onLanguageChange={setLanguageCode} />

      <div className="app__body">
        <main className="app__main">
          <Hero languageCode={languageCode} onSpeak={handleSpeak} onType={handleType} />

          {mode !== null && (
            <div ref={interactionPanelRef} className="interaction-panel">
              {mode === 'voice' && (
                <VoiceMode userId={userId} languageCode={languageCode} onCaseChanged={refreshActivity} />
              )}
              {mode === 'chat' && (
                <ChatMode
                  userId={userId}
                  languageCode={languageCode}
                  initialText={chatSeedText}
                  onExchange={addExchange}
                  onCaseChanged={refreshActivity}
                />
              )}
              <ExchangeLog exchanges={exchanges} />
            </div>
          )}

          <SchemeCardsSection languageCode={languageCode} schemes={schemes} onSelectScheme={handleSelectScheme} />

          <HowItWorks languageCode={languageCode} />
        </main>

        <aside className="app__sidebar">
          <CasePanel
            languageCode={languageCode}
            activity={activity}
            loading={activityLoading}
            onSelectActivity={handleSelectActivity}
          />
          <NeedHelpCard languageCode={languageCode} />
        </aside>
      </div>

      <Footer languageCode={languageCode} />
    </div>
  )
}
