import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import './App.css'
import { getActivity, getSchemes } from './api'
import { ActivityPage } from './components/ActivityPage'
import { AllSchemesPage } from './components/AllSchemesPage'
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
import { useStrings } from './i18n'
import { useUserId } from './hooks/useUserId'
import type { ActivityItem, Exchange, LanguageCode, SchemeSummary } from './types'

const LANGUAGE_STORAGE_KEY = 'adhikar.language_code'

type Page = 'home' | 'voice' | 'chat' | 'schemes' | 'cases'

// Voice/Chat/Schemes/Cases are real routes, not an inline panel/section toggled on the homepage
// — each is pushed via history.pushState (no router dependency; see the sibling routing note in
// architecture docs) so the browser's back/forward and a bookmarked/refreshed URL all work.
function pageFromPath(pathname: string): Page {
  if (pathname === '/voice') return 'voice'
  if (pathname === '/chat') return 'chat'
  if (pathname === '/schemes') return 'schemes'
  if (pathname === '/cases') return 'cases'
  return 'home'
}

function pathForPage(page: Page): string {
  return page === 'home' ? '/' : `/${page}`
}

export default function App() {
  const userId = useUserId()
  const [languageCode, setLanguageCode] = useState<LanguageCode>(
    () => (localStorage.getItem(LANGUAGE_STORAGE_KEY) as LanguageCode | null) ?? 'en-IN',
  )
  const strings = useStrings(languageCode)
  const [page, setPage] = useState<Page>(() => pageFromPath(window.location.pathname))
  const [chatSeedText, setChatSeedText] = useState<string | undefined>(undefined)
  const [schemes, setSchemes] = useState<SchemeSummary[]>([])
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [activityLoading, setActivityLoading] = useState(true)
  const [exchanges, setExchanges] = useState<Exchange[]>([])

  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, languageCode)
  }, [languageCode])

  // Syncs `page` with the browser's own back/forward navigation, which doesn't go through
  // `navigate()` below and so wouldn't otherwise update React state.
  useEffect(() => {
    function handlePopState() {
      setPage(pageFromPath(window.location.pathname))
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  function navigate(next: Page) {
    window.history.pushState({}, '', pathForPage(next))
    setPage(next)
    window.scrollTo(0, 0)
  }

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
    setChatSeedText(text)
    navigate('chat')
  }

  function handleSelectScheme(scheme: SchemeSummary) {
    openChatWith(strings.askAboutSchemeTemplate.replace('{scheme}', scheme.name))
  }

  function handleSelectActivity(item: ActivityItem) {
    openChatWith(strings.continueEligibilityTemplate.replace('{scheme}', item.scheme_name))
  }

  function handleSpeak() {
    navigate('voice')
  }

  function handleType() {
    setChatSeedText(undefined)
    navigate('chat')
  }

  function handleNavigate(target: 'home' | 'schemes' | 'cases') {
    navigate(target)
  }

  if (page === 'voice' || page === 'chat') {
    return (
      <ConversationPage
        page={page}
        userId={userId}
        languageCode={languageCode}
        onLanguageChange={setLanguageCode}
        chatSeedText={chatSeedText}
        exchanges={exchanges}
        onExchange={addExchange}
        onCaseChanged={refreshActivity}
        activity={activity}
        activityLoading={activityLoading}
        onSelectActivity={handleSelectActivity}
        onNavigate={handleNavigate}
      />
    )
  }

  if (page === 'schemes') {
    return (
      <AllSchemesPage
        languageCode={languageCode}
        onLanguageChange={setLanguageCode}
        schemes={schemes}
        onSelectScheme={handleSelectScheme}
        onNavigate={handleNavigate}
      />
    )
  }

  if (page === 'cases') {
    return (
      <ActivityPage
        languageCode={languageCode}
        onLanguageChange={setLanguageCode}
        activity={activity}
        loading={activityLoading}
        onSelectActivity={handleSelectActivity}
        onNavigate={handleNavigate}
      />
    )
  }

  return (
    <div className="app">
      <Header languageCode={languageCode} onLanguageChange={setLanguageCode} onNavigate={handleNavigate} />

      <div className="app__body">
        <main className="app__main">
          <Hero languageCode={languageCode} onSpeak={handleSpeak} onType={handleType} />

          <SchemeCardsSection
            languageCode={languageCode}
            schemes={schemes}
            onSelectScheme={handleSelectScheme}
            onViewAll={() => navigate('schemes')}
          />

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

// The dedicated full-page screen behind /voice and /chat — same Header/Footer chrome as the
// homepage, but the main column is just the interaction UI + exchange log (no Hero/scheme
// cards/how-it-works), and the sidebar is cut down to recent activity only (CasePanel in
// `compact` form — a handful of items, no data-secure footer note) so a user mid-conversation
// isn't shown the NeedHelpCard or the homepage's full case-history chrome.
function ConversationPage(props: {
  page: 'voice' | 'chat'
  userId: string
  languageCode: LanguageCode
  onLanguageChange: (code: LanguageCode) => void
  chatSeedText: string | undefined
  exchanges: Exchange[]
  onExchange: (transcript: string, reply: string | null) => void
  onCaseChanged: () => void
  activity: ActivityItem[]
  activityLoading: boolean
  onSelectActivity: (item: ActivityItem) => void
  onNavigate: (target: 'home' | 'schemes' | 'cases') => void
}) {
  const strings = useStrings(props.languageCode)

  return (
    <div className="app">
      <Header languageCode={props.languageCode} onLanguageChange={props.onLanguageChange} onNavigate={props.onNavigate} />

      <div className="app__body">
        <main className="app__main">
          <button type="button" className="back-link" onClick={() => props.onNavigate('home')}>
            <ArrowLeft size={16} aria-hidden="true" />
            <span>{strings.navHome}</span>
          </button>

          <div className="interaction-panel">
            {props.page === 'voice' ? (
              <VoiceMode userId={props.userId} languageCode={props.languageCode} onCaseChanged={props.onCaseChanged} />
            ) : (
              <ChatMode
                userId={props.userId}
                languageCode={props.languageCode}
                initialText={props.chatSeedText}
                onExchange={props.onExchange}
                onCaseChanged={props.onCaseChanged}
              />
            )}
            <ExchangeLog exchanges={props.exchanges} />
          </div>
        </main>

        <aside className="app__sidebar">
          <CasePanel
            compact
            languageCode={props.languageCode}
            activity={props.activity}
            loading={props.activityLoading}
            onSelectActivity={props.onSelectActivity}
          />
        </aside>
      </div>

      <Footer languageCode={props.languageCode} />
    </div>
  )
}
