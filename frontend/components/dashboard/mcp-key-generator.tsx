'use client'

import { useState } from 'react'
import { Terminal, Loader2, Copy, Check, TriangleAlert, X } from 'lucide-react'
import { apiRequest, ApiError, type McpKeyResponse } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export function McpKeyGenerator() {
  const { token } = useAuth()
  const [label, setLabel] = useState('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rawKey, setRawKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault()
    if (generating) return
    setError(null)
    setGenerating(true)
    try {
      const res = await apiRequest<McpKeyResponse>('/api-keys', {
        method: 'POST',
        token,
        body: { label: label.trim() || 'default' },
      })
      setRawKey(res.raw_key)
      setLabel('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not generate a key.')
    } finally {
      setGenerating(false)
    }
  }

  async function copyKey() {
    if (!rawKey) return
    try {
      await navigator.clipboard.writeText(rawKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <section className="rounded-2xl border border-border bg-card p-5 sm:p-6">
      <div className="flex items-center gap-2">
        <Terminal className="size-5 text-brand" />
        <h2 className="font-serif text-lg font-semibold">Programmatic access key</h2>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Generate a key to log usage from your own scripts or an MCP client.
      </p>

      {rawKey ? (
        <div className="mt-4 rounded-xl border border-mid/40 bg-mid/[0.07] p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2">
              <TriangleAlert className="mt-0.5 size-5 shrink-0 text-mid" />
              <div>
                <p className="text-sm font-semibold text-mid">Copy this key now</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  This is the only time it will ever be shown. It cannot be retrieved again. If you
                  lose it, generate a new one.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setRawKey(null)}
              aria-label="Dismiss"
              className="grid size-7 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          </div>

          <div className="mt-3 flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2.5">
            <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap font-mono text-sm text-foreground">
              {rawKey}
            </code>
            <button
              type="button"
              onClick={copyKey}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-2.5 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90"
            >
              {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleGenerate} className="mt-4 flex flex-col gap-3">
          <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Key label (e.g. local-script)"
              className="h-10 rounded-lg border border-border bg-panel px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-brand/60 focus:ring-2 focus:ring-brand/20"
            />
            <button
              type="submit"
              disabled={generating}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {generating ? <Loader2 className="size-4 animate-spin" /> : <Terminal className="size-4" />}
              Generate key
            </button>
          </div>
          {error && <p className="text-sm text-worst">{error}</p>}
        </form>
      )}
    </section>
  )
}
