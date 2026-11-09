import { ArrowRight, Keyboard, Mic } from 'lucide-react'
import { useStrings } from '../i18n'
import type { LanguageCode } from '../types'
import { Mascot } from './Mascot'

export function Hero(props: { languageCode: LanguageCode; onSpeak: () => void; onType: () => void }) {
  const strings = useStrings(props.languageCode)

  return (
    <section id="home" className="hero">
      <div className="hero__text">
        <h2 className="hero__greeting">{strings.heroGreeting}</h2>
        <p className="hero__subtitle">{strings.heroSubtitle}</p>
        <div className="hero__actions">
          <button type="button" className="btn btn--primary" onClick={props.onSpeak}>
            <Mic size={18} aria-hidden="true" />
            <span>{strings.speakNow}</span>
            <ArrowRight size={16} aria-hidden="true" className="btn__trailing-icon" />
          </button>
          <button type="button" className="btn btn--secondary" onClick={props.onType}>
            <Keyboard size={18} aria-hidden="true" />
            <span>{strings.typeMessage}</span>
            <ArrowRight size={16} aria-hidden="true" className="btn__trailing-icon" />
          </button>
        </div>
        <p className="hero__support-text">{strings.speakSupportingText}</p>
      </div>
      <Mascot languageCode={props.languageCode} />
    </section>
  )
}
