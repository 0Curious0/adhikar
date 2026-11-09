import { ArrowRight, ClipboardCheck, ClipboardList, FileCheck, Languages, Mic, Settings } from 'lucide-react'
import { useStrings } from '../i18n'
import type { LanguageCode } from '../types'

const STEP_ICONS = [Languages, Mic, ClipboardCheck, ClipboardList, FileCheck]

export function HowItWorks(props: { languageCode: LanguageCode }) {
  const strings = useStrings(props.languageCode)
  const steps = [
    { title: strings.step0Title, body: strings.step0Body },
    { title: strings.step1Title, body: strings.step1Body },
    { title: strings.step2Title, body: strings.step2Body },
    { title: strings.step3Title, body: strings.step3Body },
    { title: strings.step4Title, body: strings.step4Body },
  ]

  return (
    <section id="how-it-works" className="how-it-works">
      <div className="how-it-works__heading">
        <Settings size={20} className="how-it-works__heading-icon" aria-hidden="true" />
        <div>
          <h2 className="how-it-works__title">{strings.howItWorksTitle}</h2>
          <p className="how-it-works__subtitle">{strings.howItWorksSubtitle}</p>
        </div>
      </div>
      <ol className="how-it-works__steps">
        {steps.map((step, index) => {
          const Icon = STEP_ICONS[index]
          return (
            <li key={step.title} className="how-it-works__step">
              <div className="how-it-works__step-top">
                <span className="how-it-works__number">{index + 1}</span>
                <span className="how-it-works__icon">
                  <Icon size={18} aria-hidden="true" />
                </span>
              </div>
              <p className="how-it-works__step-title">{step.title}</p>
              <p className="how-it-works__step-body">{step.body}</p>
              {index < steps.length - 1 && (
                <ArrowRight size={16} className="how-it-works__connector" aria-hidden="true" />
              )}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
