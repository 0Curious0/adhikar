import { ChevronRight, Clock, ShieldCheck } from 'lucide-react'
import { useStrings } from '../i18n'
import type { ActivityItem, LanguageCode } from '../types'

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function CasePanel(props: {
  languageCode: LanguageCode
  activity: ActivityItem[]
  loading: boolean
  onSelectActivity: (item: ActivityItem) => void
}) {
  const strings = useStrings(props.languageCode)

  const statusLabel: Record<string, string> = {
    eligible: strings.statusEligible,
    not_eligible: strings.statusNotEligible,
    missing_fields: strings.statusMissing,
  }

  return (
    <section id="cases" className="panel">
      <h2 className="panel__title">
        <Clock size={16} aria-hidden="true" />
        {strings.yourCase}
      </h2>

      {props.loading ? (
        <p className="panel__empty">…</p>
      ) : props.activity.length === 0 ? (
        <p className="panel__empty">{strings.noCaseYet}</p>
      ) : (
        <ul className="activity-list">
          {props.activity.map((item, index) => (
            <li key={`${item.scheme_id}-${item.created_at}-${index}`} className="activity-list__item">
              <button type="button" className="activity-list__row" onClick={() => props.onSelectActivity(item)}>
                <span
                  className={`activity-list__dot activity-list__dot--${item.eligibility_status}`}
                  aria-hidden="true"
                />
                <span className="activity-list__text">
                  <span className="activity-list__scheme">{item.scheme_name}</span>
                  <span className="activity-list__meta">
                    {statusLabel[item.eligibility_status]} · {formatTimestamp(item.created_at)}
                  </span>
                </span>
                <ChevronRight size={16} className="activity-list__chevron" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="data-secure">
        <ShieldCheck size={18} className="data-secure__icon" aria-hidden="true" />
        <div>
          <p className="data-secure__title">{strings.dataSecureTitle}</p>
          <p className="data-secure__body">{strings.privacyNote}</p>
        </div>
      </div>
    </section>
  )
}
