'use client'

import { Sparkles, BarChart3, AlertCircle } from 'lucide-react'
import { formatCost, formatTokens, type AdvisorResponse } from '@/lib/api'
import { useApiSWR } from '@/hooks/use-api-swr'

function humanizeKey(key: string) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bId\b/, 'ID')
}

function formatValue(key: string, value: unknown): string {
  const lower = key.toLowerCase()
  if (typeof value === 'number') {
    if (lower.includes('cost') || lower.includes('spend') || lower.includes('usd')) {
      return formatCost(value)
    }
    if (lower.includes('token')) return formatTokens(value)
    if (Number.isInteger(value)) return value.toLocaleString('en-US')
    return value.toFixed(2)
  }
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (value === null || value === undefined) return 'n/a'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function AdvisorSection() {
  const { data, error, isLoading } = useApiSWR<AdvisorResponse>('/advisor')

  const patternEntries =
    data?.pattern && typeof data.pattern === 'object'
      ? Object.entries(data.pattern).filter(([, v]) => typeof v !== 'object' || v === null)
      : []

  return (
    <div className="flex flex-col gap-4">
      {/* AI Insight card, deliberately distinct from raw stats */}
      <section className="relative overflow-hidden rounded-2xl border border-brand/30 bg-gradient-to-br from-brand/[0.08] to-transparent p-5 sm:p-6">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-8 -top-8 size-32 rounded-full bg-brand/10 blur-2xl"
        />
        <div className="relative flex items-center gap-2">
          <span className="grid size-8 place-items-center rounded-lg bg-brand/15 text-brand">
            <Sparkles className="size-4" />
          </span>
          <div>
            <h2 className="font-serif text-lg font-semibold">AI Insight</h2>
            <p className="text-xs text-muted-foreground">Generated from your usage patterns</p>
          </div>
        </div>

        <div className="relative mt-4">
          {isLoading ? (
            <div className="space-y-2">
              <div className="h-4 w-full animate-pulse rounded bg-muted" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-muted" />
              <div className="h-4 w-4/6 animate-pulse rounded bg-muted" />
            </div>
          ) : error ? (
            <div className="flex items-start gap-2 text-sm text-muted-foreground">
              <AlertCircle className="mt-0.5 size-4 shrink-0 text-mid" />
              <p>
                No advice yet. Connect a provider and price a few prompts. The Advisor needs some
                usage to analyze.
              </p>
            </div>
          ) : (
            <p className="text-pretty font-serif text-lg leading-relaxed text-foreground">
              {data?.recommendation || 'No recommendation available yet.'}
            </p>
          )}
        </div>
      </section>

      {/* Raw usage stats */}
      <section className="rounded-2xl border border-border bg-card p-5 sm:p-6">
        <div className="flex items-center gap-2">
          <BarChart3 className="size-5 text-muted-foreground" />
          <h2 className="font-serif text-lg font-semibold">Usage patterns</h2>
        </div>

        {isLoading ? (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
        ) : patternEntries.length === 0 ? (
          <p className="mt-4 rounded-lg border border-dashed border-border px-4 py-5 text-center text-sm text-muted-foreground">
            Usage stats will appear here once you&apos;ve logged some priced prompts.
          </p>
        ) : (
          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {patternEntries.map(([key, value]) => (
              <div key={key} className="rounded-lg border border-border bg-panel px-3 py-3">
                <dt className="text-xs text-muted-foreground">{humanizeKey(key)}</dt>
                <dd className="mt-1 font-mono text-base font-semibold tabular-nums text-foreground">
                  {formatValue(key, value)}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </section>
    </div>
  )
}
