'use client'

import { useState } from 'react'
import { KeyRound, Plus, Trash2, Loader2, Info, Check } from 'lucide-react'
import {
  apiRequest,
  ApiError,
  PROVIDER_LABELS,
  type ConnectedKey,
  type Provider,
} from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { useApiSWR } from '@/hooks/use-api-swr'
import { cn } from '@/lib/utils'

const PROVIDERS: Provider[] = ['anthropic', 'groq', 'openai']

export function KeysPanel() {
  const { token } = useAuth()
  const { data: keys, isLoading, mutate } = useApiSWR<ConnectedKey[]>('/keys')

  const [provider, setProvider] = useState<Provider>('anthropic')
  const [apiKey, setApiKey] = useState('')
  const [label, setLabel] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | number | null>(null)

  const connected = keys ?? []
  const connectedProviders = new Set(connected.map((k) => k.provider))

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey.trim() || submitting) return
    setError(null)
    setSubmitting(true)
    try {
      await apiRequest('/keys', {
        method: 'POST',
        token,
        body: { provider, api_key: apiKey.trim(), label: label.trim() || undefined },
      })
      setApiKey('')
      setLabel('')
      await mutate()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not connect that key.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id: string | number) {
    setDeletingId(id)
    try {
      await apiRequest(`/keys/${id}`, { method: 'DELETE', token })
      await mutate()
    } catch {
      /* keep row on failure */
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="rounded-2xl border border-border bg-card p-5 sm:p-6">
      <div className="flex items-center gap-2">
        <KeyRound className="size-5 text-brand" />
        <h2 className="font-serif text-lg font-semibold">Connected providers</h2>
      </div>

      <div className="mt-2 flex items-start gap-2 rounded-lg border border-border bg-secondary/50 px-3 py-2.5 text-xs text-muted-foreground">
        <Info className="mt-0.5 size-3.5 shrink-0 text-brand" />
        <p>
          Paste a <span className="font-medium text-foreground">regular API key</span>, the same
          one you already use in your code, not an admin key. It unlocks live pricing for that
          provider on the leaderboard.
        </p>
      </div>

      {/* Connected list */}
      <div className="mt-4 flex flex-col gap-2">
        {isLoading ? (
          <div className="h-14 animate-pulse rounded-lg bg-muted" />
        ) : connected.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border px-4 py-5 text-center text-sm text-muted-foreground">
            No providers connected yet. Add one below to unlock its rows.
          </p>
        ) : (
          connected.map((k) => (
            <div
              key={String(k.id)}
              className="flex items-center justify-between rounded-lg border border-border bg-panel px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <span className="grid size-8 place-items-center rounded-md bg-best/15 text-best">
                  <Check className="size-4" />
                </span>
                <div>
                  <p className="text-sm font-medium">
                    {PROVIDER_LABELS[k.provider as Provider] ?? k.provider}
                  </p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {k.label ? k.label : 'connected'}
                    {k.last_four ? ` · ••••${k.last_four}` : ''}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleDelete(k.id)}
                disabled={deletingId === k.id}
                aria-label={`Disconnect ${PROVIDER_LABELS[k.provider as Provider] ?? k.provider}`}
                className="grid size-8 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-worst/10 hover:text-worst disabled:opacity-50"
              >
                {deletingId === k.id ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4" />
                )}
              </button>
            </div>
          ))
        )}
      </div>

      {/* Add form */}
      <form onSubmit={handleAdd} className="mt-4 flex flex-col gap-3 border-t border-border pt-4">
        <div className="flex flex-wrap gap-2">
          {PROVIDERS.map((p) => {
            const already = connectedProviders.has(p)
            return (
              <button
                key={p}
                type="button"
                onClick={() => setProvider(p)}
                className={cn(
                  'rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors',
                  provider === p
                    ? 'border-brand/60 bg-brand/10 text-brand'
                    : 'border-border bg-panel text-muted-foreground hover:text-foreground',
                )}
              >
                {PROVIDER_LABELS[p]}
                {already && <span className="ml-1.5 text-xs text-best">✓</span>}
              </button>
            )
          })}
        </div>

        <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={`Your ${PROVIDER_LABELS[provider]} API key`}
            className="h-10 rounded-lg border border-border bg-panel px-3 font-mono text-sm outline-none transition-colors placeholder:font-sans placeholder:text-muted-foreground/60 focus:border-brand/60 focus:ring-2 focus:ring-brand/20"
            autoComplete="off"
          />
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Label (optional)"
            className="h-10 rounded-lg border border-border bg-panel px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-brand/60 focus:ring-2 focus:ring-brand/20 sm:w-40"
          />
        </div>

        {error && <p className="text-sm text-worst">{error}</p>}

        <button
          type="submit"
          disabled={!apiKey.trim() || submitting}
          className="inline-flex h-10 items-center justify-center gap-2 self-start rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
          Connect {PROVIDER_LABELS[provider]}
        </button>
      </form>
    </section>
  )
}
