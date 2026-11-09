import { BookOpen, Gavel, Globe, Headphones } from 'lucide-react'
import whatsappLogo from '../assets/whatsapplogo.png'
import { useStrings } from '../i18n'
import type { LanguageCode } from '../types'

// WhatsApp isn't integrated (deferred post-MVP) — the row is deliberately non-interactive, even
// though it now uses the real provided brand asset (whatsapplogo.png) rather than a neutral
// Lucide icon. CPGRAMS/MyScheme are real external government portals (grievance redressal and
// scheme discovery respectively), not part of this app's own backend — opened in a new tab so
// the user's in-progress conversation here isn't lost by navigating away.
export function NeedHelpCard(props: { languageCode: LanguageCode }) {
  const strings = useStrings(props.languageCode)

  return (
    <section id="help" className="panel need-help">
      <h2 className="panel__title">
        <Headphones size={16} aria-hidden="true" />
        {strings.needHelpTitle}
      </h2>

      <ul className="support-list">
        <li>
          <a href="https://pgportal.gov.in/" target="_blank" rel="noopener noreferrer" className="support-row">
            <span className="support-row__icon support-row__icon--pink">
              <Gavel size={18} aria-hidden="true" />
            </span>
            <span className="support-row__text">
              <span className="support-row__label">{strings.cpgramsLabel}</span>
              <span className="support-row__subtitle">{strings.cpgramsSubtitle}</span>
            </span>
          </a>
        </li>
        <li>
          <a href="https://www.myscheme.gov.in/" target="_blank" rel="noopener noreferrer" className="support-row">
            <span className="support-row__icon support-row__icon--pink">
              <Globe size={18} aria-hidden="true" />
            </span>
            <span className="support-row__text">
              <span className="support-row__label">{strings.mySchemeLabel}</span>
              <span className="support-row__subtitle">{strings.mySchemeSubtitle}</span>
            </span>
          </a>
        </li>
        <li>
          <span className="support-row support-row--disabled" aria-disabled="true">
            <span className="support-row__icon support-row__icon--green">
              <img src={whatsappLogo} alt="" className="support-row__icon-image" aria-hidden="true" />
            </span>
            <span className="support-row__text">
              <span className="support-row__label">{strings.whatsappLabel}</span>
              <span className="support-row__subtitle support-row__subtitle--coming-soon">{strings.whatsappSubtitle}</span>
            </span>
          </span>
        </li>
        <li>
          <a href="#how-it-works" className="support-row">
            <span className="support-row__icon support-row__icon--pink">
              <BookOpen size={18} aria-hidden="true" />
            </span>
            <span className="support-row__text">
              <span className="support-row__label">{strings.userGuideLabel}</span>
              <span className="support-row__subtitle">{strings.userGuideSubtitle}</span>
            </span>
          </a>
        </li>
      </ul>
    </section>
  )
}
