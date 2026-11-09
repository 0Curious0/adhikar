import mascotImg from '../assets/mascot.png'
import { useStrings } from '../i18n'
import type { LanguageCode } from '../types'

export function Mascot(props: { languageCode: LanguageCode }) {
  const strings = useStrings(props.languageCode)

  return (
    <div className="mascot">
      <div className="mascot__bubble">{strings.heroBubble}</div>
      <img src={mascotImg} className="mascot__figure" alt="" />
    </div>
  )
}
