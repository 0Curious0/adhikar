import { ArrowRight, HeartPulse, Landmark, Sprout, UserRound, Users, Wheat, type LucideIcon } from 'lucide-react'
import { useStrings } from '../i18n'
import type { LanguageCode, SchemeSummary } from '../types'

// The backend loads 7 scheme documents (widow pension has a central + 2 state variants — see
// adhikar.schemes' widow_pension/ directory), but the design calls for exactly 5 category cards.
// This curates which scheme_id represents each category's card: the central IGNWPS scheme
// stands in for "Widow Pension" as a topic, since classify_scheme/NLU resolves the actual
// state-specific scheme from the conversation itself, not from which card was clicked.
const CATEGORY_SCHEME_IDS: { scheme_id: string; Icon: LucideIcon }[] = [
  { scheme_id: 'ignwps', Icon: UserRound },
  { scheme_id: 'pm_kisan', Icon: Sprout },
  { scheme_id: 'ayushman_bharat_pmjay', Icon: HeartPulse },
  { scheme_id: 'nfsa_targeted_public_distribution_system', Icon: Wheat },
  { scheme_id: 'vb_g_ram_g', Icon: Users },
]

export function SchemeCardsSection(props: {
  languageCode: LanguageCode
  schemes: SchemeSummary[]
  onSelectScheme: (scheme: SchemeSummary) => void
}) {
  const strings = useStrings(props.languageCode)
  const byId = new Map(props.schemes.map((scheme) => [scheme.scheme_id, scheme]))
  const cards = CATEGORY_SCHEME_IDS.map(({ scheme_id, Icon }) => ({ scheme: byId.get(scheme_id), Icon })).filter(
    (card): card is { scheme: SchemeSummary; Icon: (typeof CATEGORY_SCHEME_IDS)[number]['Icon'] } =>
      card.scheme !== undefined,
  )

  return (
    <section id="schemes" className="schemes-section">
      <div className="schemes-section__header">
        <div className="schemes-section__heading">
          <Landmark size={20} className="schemes-section__icon" aria-hidden="true" />
          <div>
            <h2 className="schemes-section__title">{strings.governmentSchemes}</h2>
            <p className="schemes-section__subtitle">{strings.schemesSectionSubtitle}</p>
          </div>
        </div>
        <a href="#schemes" className="schemes-section__view-all">
          {strings.viewAllSchemes}
          <ArrowRight size={14} aria-hidden="true" />
        </a>
      </div>

      <div className="scheme-cards">
        {cards.map(({ scheme, Icon }) => (
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
        ))}
      </div>
    </section>
  )
}
