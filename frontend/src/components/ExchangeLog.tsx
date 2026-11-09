import type { Exchange } from '../types'

export function ExchangeLog(props: { exchanges: Exchange[] }) {
  if (props.exchanges.length === 0) return null

  return (
    <ul className="exchange-log">
      {props.exchanges.map((exchange) => (
        <li key={exchange.id} className="exchange-log__item">
          <p className="exchange-log__transcript">{exchange.transcript}</p>
          {exchange.reply && <p className="exchange-log__reply">{exchange.reply}</p>}
        </li>
      ))}
    </ul>
  )
}
