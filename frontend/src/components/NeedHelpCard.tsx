import { BookOpen, Headphones, MessageCircle, Phone } from 'lucide-react'
import { useStrings } from '../i18n'
import type { LanguageCode } from '../types'

// WhatsApp isn't integrated (deferred post-MVP) — the row is deliberately non-interactive, and
// uses a neutral Lucide icon rather than WhatsApp's trademarked logo, which (like the State
// Emblem) isn't ours to reproduce without authorization. Swap in a provided brand asset later.
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
          <a href="tel:112" className="support-row">
            <span className="support-row__icon support-row__icon--pink">
              <Phone size={18} aria-hidden="true" />
            </span>
            <span className="support-row__text">
              <span className="support-row__label">{strings.helplineLabel}</span>
              <span className="support-row__subtitle">{strings.helplineSubtitle}</span>
            </span>
          </a>
        </li>
        <li>
          <span className="support-row support-row--disabled" aria-disabled="true">
            <span className="support-row__icon support-row__icon--green">
              <MessageCircle size={18} aria-hidden="true" />
            </span>
            <span className="support-row__text">
              <span className="support-row__label">{strings.whatsappLabel}</span>
              <span className="support-row__subtitle">{strings.whatsappSubtitle}</span>
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
