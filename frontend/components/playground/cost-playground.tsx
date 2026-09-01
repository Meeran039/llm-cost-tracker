'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence } from 'motion/react'
import { Sparkles } from 'lucide-react'
import {
  apiRequest,
  extractCost,
  MODELS,
  type ConnectedKey,
  type Provider,
  type UsageLogResponse,
} from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { useDebounce } from '@/hooks/use-debounce'
import { LeaderboardRow, type RowData, type Tier } from './leaderboard-row'

const SAMPLE_PROMPT =
  'You are a senior financial analyst. Summarize the attached quarterly earnings report into five bullet points, then draft a short email to the CFO highlighting the biggest risk and one recommended action.'

function keyOf(provider: string, model: string) {
  return `${provider}:${model}`
}

function initialRows(): Record<string, RowData> {
  const map: Record<string, RowData> = {}
  for (const m of MODELS) {
    map[keyOf(m.provider, m.model)] = {
      key: keyOf(m.provider, m.model),
      provider: m.provider,
      label: m.label,
      model: m.model,
      status: 'idle',
      cost: null,
      inputTokens: null,
      outputTokens: null,
      contextWindow: null,
      error: null,
    }
  }
  return map
}

export function CostPlayground() {
  const { token } = useAuth()
  const [prompt, setPrompt] = useState('')
  const [expectedOutput, setExpectedOutput] = useState(500)
  const [rows, setRows] = useState<Record<string, RowData>>(initialRows)
  const [connectedProviders, setConnectedProviders] = useState<Set<Provider>>(new Set())
  const abortRef = useRef<AbortController | null>(null)

  const debouncedPrompt = useDebounce(prompt, 400)
  const debouncedOutput = useDebounce(expectedOutput, 400)

  // Discover which providers have a connected key so we can price them live.
  useEffect(() => {
    if (!token) {
      setConnectedProviders(new Set())
      return
    }
    let cancelled = false
    apiRequest<ConnectedKey[]>('/keys', { token })
      .then((keys) => {
        if (cancelled) return
        const set = new Set<Provider>()
        for (const k of keys ?? []) {
          if (k.provider) set.add(k.provider as Provider)
        }
        setConnectedProviders(set)
      })
      .catch(() => {
        /* non-fatal: leaderboard still works for OpenAI */
      })
    return () => {
      cancelled = true
    }
  }, [token])

  const isComputable = useCallback(
    (provider: Provider, requiresKey: boolean) =>
      !requiresKey || connectedProviders.has(provider),
    [connectedProviders],
  )

  // Recompute costs whenever the debounced prompt, output size, or auth changes.
  useEffect(() => {
    abortRef.current?.abort()

    const trimmed = debouncedPrompt.trim()
    if (!trimmed) {
      setRows((prev) => {
        const next = { ...prev }
        for (const k of Object.keys(next)) {
          next[k] = { ...next[k], status: 'idle', cost: null, inputTokens: null, outputTokens: null, error: null }
        }
        return next
      })
      return
    }

    const controller = new AbortController()
    abortRef.current = controller

    // Mark computable rows loading (keep last cost for stable ordering); lock the rest.
    setRows((prev) => {
      const next = { ...prev }
      for (const m of MODELS) {
        const k = keyOf(m.provider, m.model)
        if (isComputable(m.provider, m.requiresKey)) {
          next[k] = { ...next[k], status: 'loading', error: null }
        } else {
          next[k] = { ...next[k], status: 'locked', cost: null, inputTokens: null, outputTokens: null, error: null }
        }
      }
      return next
    })

    for (const m of MODELS) {
      if (!isComputable(m.provider, m.requiresKey)) continue
      const k = keyOf(m.provider, m.model)
      apiRequest<UsageLogResponse>('/usage/log', {
        method: 'POST',
        token,
        signal: controller.signal,
        body: {
          provider: m.provider,
          model: m.model,
          prompt: trimmed,
          expected_output_tokens: debouncedOutput,
        },
      })
        .then((res) => {
          if (controller.signal.aborted) return
          const cost = extractCost(res)
          const fits = res.fits_context_window !== false
          setRows((prev) => ({
            ...prev,
            [k]: {
              ...prev[k],
              status: fits ? 'ok' : 'unfit',
              cost,
              inputTokens:
                typeof res.input_tokens === 'number'
                  ? res.input_tokens
                  : typeof res.prompt_tokens === 'number'
                    ? res.prompt_tokens
                    : null,
              outputTokens: typeof res.output_tokens === 'number' ? res.output_tokens : debouncedOutput,
              contextWindow: typeof res.context_window === 'number' ? res.context_window : null,
              error: null,
            },
          }))
        })
        .catch((err) => {
          if (controller.signal.aborted || err?.name === 'AbortError') return
          setRows((prev) => ({
            ...prev,
            [k]: { ...prev[k], status: 'error', error: err?.message ?? 'Failed to price' },
          }))
        })
    }

    return () => controller.abort()
  }, [debouncedPrompt, debouncedOutput, token, isComputable])

  const { ordered, tierMap, rankMap, maxCost } = useMemo(() => {
    const all = Object.values(rows)
    const locked = all.filter((r) => r.status === 'locked')
    const active = all.filter((r) => r.status !== 'locked')

    // Sort active rows: priced rows by cost asc, unfit sink, idle/error/loading keep near last cost.
    const sortValue = (r: RowData) => {
      if (r.status === 'unfit') return Number.MAX_SAFE_INTEGER - 1
      if (r.cost !== null) return r.cost
      return Number.MAX_SAFE_INTEGER
    }
    active.sort((a, b) => sortValue(a) - sortValue(b))

    const okRows = active.filter((r) => r.status === 'ok' && r.cost !== null)
    const costs = okRows.map((r) => r.cost as number)
    const max = costs.length ? Math.max(...costs) : 0

    const tierMap: Record<string, Tier> = {}
    const rankMap: Record<string, number | null> = {}
    okRows.forEach((r, i) => {
      rankMap[r.key] = i + 1
      if (okRows.length === 1) tierMap[r.key] = 'best'
      else if (i === 0) tierMap[r.key] = 'best'
      else if (i === okRows.length - 1) tierMap[r.key] = 'worst'
      else tierMap[r.key] = 'mid'
    })

    return { ordered: [...active, ...locked], tierMap, rankMap, maxCost: max }
  }, [rows])

  const hasPrompt = debouncedPrompt.trim().length > 0

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      {/* Prompt input */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <label htmlFor="prompt" className="text-sm font-medium text-muted-foreground">
            Your prompt
          </label>
          <button
            type="button"
            onClick={() => setPrompt(SAMPLE_PROMPT)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-brand transition-opacity hover:opacity-80"
          >
            <Sparkles className="size-3.5" />
            Try a sample
          </button>
        </div>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Paste or type a prompt. Costs update live as you type."
          className="min-h-[220px] w-full resize-y rounded-xl border border-border bg-panel p-4 font-mono text-sm leading-relaxed text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-brand/60 focus:ring-2 focus:ring-brand/20 lg:min-h-[340px]"
          spellCheck={false}
        />
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-panel/60 px-3 py-2.5">
          <label htmlFor="output" className="text-xs font-medium text-muted-foreground">
            Expected output length
          </label>
          <div className="flex items-center gap-3">
            <input
              id="output"
              type="range"
              min={0}
              max={4000}
              step={50}
              value={expectedOutput}
              onChange={(e) => setExpectedOutput(Number(e.target.value))}
              className="h-1 w-32 cursor-pointer appearance-none rounded-full bg-muted accent-brand sm:w-44"
            />
            <span className="w-24 text-right font-mono text-xs tabular-nums text-foreground">
              {expectedOutput.toLocaleString()} tok
            </span>
          </div>
        </div>
      </div>

      {/* Leaderboard */}
      <div className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <h2 className="font-serif text-lg font-semibold">Cost leaderboard</h2>
          <span className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
            {hasPrompt ? 'per request' : 'awaiting prompt'}
          </span>
        </div>

        {!hasPrompt && (
          <p className="rounded-lg border border-dashed border-border bg-panel/40 px-4 py-6 text-center text-sm text-muted-foreground">
            Start typing on the left and models will rank themselves here, cheapest first.
          </p>
        )}

        <ul className="flex flex-col gap-2">
          <AnimatePresence initial={false}>
            {(hasPrompt ? ordered : []).map((row) => (
              <LeaderboardRow
                key={row.key}
                row={row}
                rank={rankMap[row.key] ?? null}
                tier={tierMap[row.key] ?? null}
                ratio={maxCost > 0 && row.cost !== null ? row.cost / maxCost : 0}
              />
            ))}
          </AnimatePresence>
        </ul>
      </div>
    </div>
  )
}
