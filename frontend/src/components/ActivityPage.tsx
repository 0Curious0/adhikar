import { ArrowLeft } from 'lucide-react'
import { useStrings } from '../i18n'
import type { ActivityItem, LanguageCode } from '../types'
import { CasePanel } from './CasePanel'
import { Footer } from './Footer'
import { Header } from './Header'

// The full, uncapped activity list, full-width — unlike the homepage/Voice/Chat sidebar's
// CasePanel (which is either capped at 3 items via `compact` or squeezed into a 360px column).
export function ActivityPage(props: {
  languageCode: LanguageCode
  onLanguageChange: (code: LanguageCode) => void
  activity: ActivityItem[]
  loading: boolean
  onSelectActivity: (item: ActivityItem) => void
  onNavigate: (target: 'home' | 'schemes' | 'cases') => void
}) {
  const strings = useStrings(props.languageCode)

  return (
    <div className="app">
      <Header languageCode={props.languageCode} onLanguageChange={props.onLanguageChange} onNavigate={props.onNavigate} />

      <div className="app__body app__body--full">
        <main className="app__main">
          <button type="button" className="back-link" onClick={() => props.onNavigate('home')}>
            <ArrowLeft size={16} aria-hidden="true" />
            <span>{strings.navHome}</span>
          </button>

          <CasePanel
            languageCode={props.languageCode}
            activity={props.activity}
            loading={props.loading}
            onSelectActivity={props.onSelectActivity}
          />
        </main>
      </div>

      <Footer languageCode={props.languageCode} />
    </div>
  )
}
