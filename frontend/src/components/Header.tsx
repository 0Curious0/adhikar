import { ChevronDown, CircleHelp, Folder, House, Landmark, Languages, Menu, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import logo from '../assets/logo.png'
import { useStrings } from '../i18n'
import type { LanguageCode } from '../types'

const LANGUAGES: { code: LanguageCode; label: string }[] = [
  { code: 'hi-IN', label: 'हिंदी' },
  { code: 'en-IN', label: 'English' },
  { code: 'bn-IN', label: 'বাংলা' },
  { code: 'gu-IN', label: 'ગુજરાતી' },
  { code: 'kn-IN', label: 'ಕನ್ನಡ' },
  { code: 'ml-IN', label: 'മലയാളം' },
  { code: 'mr-IN', label: 'मराठी' },
  { code: 'pa-IN', label: 'ਪੰਜਾਬੀ' },
  { code: 'ta-IN', label: 'தமிழ்' },
  { code: 'te-IN', label: 'తెలుగు' },
]

export function Header(props: { languageCode: LanguageCode; onLanguageChange: (code: LanguageCode) => void }) {
  const strings = useStrings(props.languageCode)
  const [showMobileNav, setShowMobileNav] = useState(false)
  const [showLanguageMenu, setShowLanguageMenu] = useState(false)
  const languageMenuRef = useRef<HTMLDivElement | null>(null)
  const mobileNavId = useId()
  const languageMenuId = useId()
  const navItems = [
    { href: '#home', label: strings.navHome, Icon: House },
    { href: '#schemes', label: strings.navSchemes, Icon: Landmark },
    { href: '#cases', label: strings.navCases, Icon: Folder },
    { href: '#help', label: strings.navHelp, Icon: CircleHelp },
  ]
  const currentLanguage = LANGUAGES.find((lang) => lang.code === props.languageCode)

  // Close the language dropdown on an outside click — with 10 options it's a popover, not an
  // always-visible segmented control, so it needs the usual dismiss-on-outside-click behavior.
  useEffect(() => {
    if (!showLanguageMenu) return
    function handleClick(event: MouseEvent) {
      if (languageMenuRef.current && !languageMenuRef.current.contains(event.target as Node)) {
        setShowLanguageMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [showLanguageMenu])

  return (
    <header className="header">
      <div className="header__brand">
        <img src={logo} className="header__emblem" alt="Adhikar logo" />
        <div>
          <h1 className="header__title">Adhikar</h1>
          <p className="header__tagline">{strings.tagline}</p>
        </div>
      </div>

      <nav className="header__nav" aria-label="Sections">
        {navItems.map(({ href, label, Icon }) => (
          <a key={href} href={href} className="header__nav-link">
            <Icon size={15} aria-hidden="true" />
            <span>{label}</span>
          </a>
        ))}
      </nav>

      <div className="header__controls">
        <button
          type="button"
          className="header__menu-btn"
          aria-label="Menu"
          aria-haspopup="true"
          aria-expanded={showMobileNav}
          aria-controls={mobileNavId}
          onClick={() => setShowMobileNav((open) => !open)}
        >
          {showMobileNav ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
        </button>

        <div className="header__language-picker" ref={languageMenuRef}>
          <button
            type="button"
            className="header__language-btn"
            aria-haspopup="true"
            aria-expanded={showLanguageMenu}
            aria-controls={languageMenuId}
            onClick={() => setShowLanguageMenu((open) => !open)}
          >
            <Languages size={16} aria-hidden="true" />
            <span>{currentLanguage?.label}</span>
            <ChevronDown size={14} aria-hidden="true" />
          </button>
          {showLanguageMenu && (
            <ul id={languageMenuId} className="header__language-menu" role="menu" aria-label="Choose language">
              {LANGUAGES.map((lang) => (
                <li key={lang.code}>
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={lang.code === props.languageCode}
                    className={`header__language-option${lang.code === props.languageCode ? ' header__language-option--active' : ''}`}
                    onClick={() => {
                      props.onLanguageChange(lang.code)
                      setShowLanguageMenu(false)
                    }}
                  >
                    {lang.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {showMobileNav && (
        <nav id={mobileNavId} className="header__mobile-nav" aria-label="Sections">
          {navItems.map(({ href, label, Icon }) => (
            <a key={href} href={href} className="header__nav-link" onClick={() => setShowMobileNav(false)}>
              <Icon size={16} aria-hidden="true" />
              <span>{label}</span>
            </a>
          ))}
        </nav>
      )}
    </header>
  )
}