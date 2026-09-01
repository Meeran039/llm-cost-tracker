import { TrendingDown, TrendingUp } from 'lucide-react'

interface Quote {
  label: string
  price: string
  dir: 'up' | 'down'
}

// Illustrative reference prices for the marquee. The real numbers are computed
// live in the playground; these set the "trading terminal" tone.
const QUOTES: Quote[] = [
  { label: 'gpt-4o-mini', price: '$0.0004', dir: 'down' },
  { label: 'claude-3.5-haiku', price: '$0.0011', dir: 'up' },
  { label: 'llama-3.1-8b', price: '$0.0002', dir: 'down' },
  { label: 'gpt-4o', price: '$0.0092', dir: 'up' },
  { label: 'claude-3.5-sonnet', price: '$0.0135', dir: 'up' },
  { label: 'llama-3.3-70b', price: '$0.0018', dir: 'down' },
  { label: 'gpt-4.1-mini', price: '$0.0006', dir: 'down' },
  { label: 'claude-3-opus', price: '$0.0410', dir: 'up' },
]

function Row() {
  return (
    <div className="flex shrink-0 items-center" aria-hidden="true">
      {QUOTES.map((q, i) => (
        <div key={`${q.label}-${i}`} className="flex items-center gap-2 px-5 py-2">
          <span className="font-mono text-xs text-muted-foreground">{q.label}</span>
          <span
            className={
              'inline-flex items-center gap-1 font-mono text-xs tabular-nums ' +
              (q.dir === 'down' ? 'text-best' : 'text-worst')
            }
          >
            {q.dir === 'down' ? (
              <TrendingDown className="size-3" />
            ) : (
              <TrendingUp className="size-3" />
            )}
            {q.price}
          </span>
          <span className="text-border">/</span>
        </div>
      ))}
    </div>
  )
}

export function TickerTape() {
  return (
    <div className="relative overflow-hidden rounded-full border border-border bg-panel/60">
      {/* edge fades */}
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-background to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-background to-transparent" />
      <div className="flex w-max animate-ticker">
        <Row />
        <Row />
      </div>
    </div>
  )
}
