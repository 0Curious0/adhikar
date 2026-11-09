import { useStrings } from '../i18n'
import type { LanguageCode } from '../types'

// About/Privacy/Terms/Contact have no corresponding pages in this MVP — rendered as inert links
// (no real destination, same honesty stance as the rest of the app) rather than fabricated routes.
export function Footer(props: { languageCode: LanguageCode }) {
  const strings = useStrings(props.languageCode)
  const links = [strings.footerAbout, strings.footerPrivacy, strings.footerTerms, strings.footerContact]

  return (
    <footer className="footer">
      <div className="footer__brand">
        <span className="footer__name">Adhikar</span>
        <span className="footer__tagline">{strings.footerTagline}</span>
      </div>
      <nav className="footer__links" aria-label="Footer">
        {links.map((label) => (
          <a key={label} href="#" onClick={(event) => event.preventDefault()}>
            {label}
          </a>
        ))}
      </nav>
    </footer>
  )
}
