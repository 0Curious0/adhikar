import { ArrowLeft, ArrowRight, HeartPulse, Landmark, Sprout, UserRound, Users, Wheat, type LucideIcon } from 'lucide-react'
import { useStrings } from '../i18n'
import type { LanguageCode, SchemeSummary } from '../types'
import { Footer } from './Footer'
import { Header } from './Header'

// Covers every scheme_id the backend currently loads (see adhikar.schemes.loader) — unlike
// SchemeCardsSection's curated 5-card homepage preview, this page shows everything, so every
// scheme_id needs an icon, including the two widow-pension state variants beside the central
// one. Anything not listed here (a newly-added scheme) still renders with the Landmark fallback.
const SCHEME_ICONS: Record<string, LucideIcon> = {
  ignwps: UserRound,
  mukhya_mantri_ekal_nari_samman_pension_rajasthan: UserRound,
  nirashrit_mahila_pension_uttar_pradesh: UserRound,
  pm_kisan: Sprout,
  ayushman_bharat_pmjay: HeartPulse,
  nfsa_targeted_public_distribution_system: Wheat,
  vb_g_ram_g: Users,
}

export function AllSchemesPage(props: {
  languageCode: LanguageCode
  onLanguageChange: (code: LanguageCode) => void
  schemes: SchemeSummary[]
  onSelectScheme: (scheme: SchemeSummary) => void
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

          <section className="schemes-section">
            <div className="schemes-section__header">
              <div className="schemes-section__heading">
                <Landmark size={20} className="schemes-section__icon" aria-hidden="true" />
                <div>
                  <h2 className="schemes-section__title">{strings.governmentSchemes}</h2>
                  <p className="schemes-section__subtitle">{strings.schemesSectionSubtitle}</p>
                </div>
              </div>
            </div>

            <div className="scheme-cards">
              {props.schemes.map((scheme) => {
                const Icon = SCHEME_ICONS[scheme.scheme_id] ?? Landmark
                return (
                  <button
                    key={scheme.scheme_id}
                    type="button"
                    className="scheme-card"
                    title={`${scheme.name} — ${scheme.description}`}
                    onClick={() => props.onSelectScheme(scheme)}
                  >
                    <span className="scheme-card__icon">
                      <Icon size={28} aria-hidden="true" />
                    </span>
                    <p className="scheme-card__name">{scheme.name}</p>
                    <p className="scheme-card__description">{scheme.description}</p>
                    <ArrowRight size={16} className="scheme-card__arrow" aria-hidden="true" />
                  </button>
                )
              })}
            </div>
          </section>
        </main>
      </div>

      <Footer languageCode={props.languageCode} />
    </div>
  )
}
