'use client'

import { useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Check, X, Loader2, ArrowLeft } from 'lucide-react'
import { Logo } from '@/components/logo'
import { useAuth } from '@/lib/auth-context'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Rule {
  label: string
  test: (v: string) => boolean
}

const PASSWORD_RULES: Rule[] = [
  { label: '8+ characters', test: (v) => v.length >= 8 },
  { label: 'Uppercase letter', test: (v) => /[A-Z]/.test(v) },
  { label: 'Lowercase letter', test: (v) => /[a-z]/.test(v) },
  { label: 'Number', test: (v) => /[0-9]/.test(v) },
  { label: 'Symbol', test: (v) => /[^A-Za-z0-9]/.test(v) },
]

export function AuthForm() {
  const router = useRouter()
  const params = useSearchParams()
  const { login, signup } = useAuth()

  const [mode, setMode] = useState<'login' | 'signup'>(
    params.get('mode') === 'signup' ? 'signup' : 'login',
  )
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const passwordChecks = useMemo(
    () => PASSWORD_RULES.map((r) => ({ label: r.label, ok: r.test(password) })),
    [password],
  )
  const passwordValid = passwordChecks.every((c) => c.ok)

  const canSubmit =
    email.trim().length > 0 && password.length > 0 && (mode === 'login' || passwordValid)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit || submitting) return
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'signup') {
        await signup(email.trim(), password)
      } else {
        await login(email.trim(), password)
      }
      router.push('/dashboard')
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'Something went wrong. Please try again.'
      setError(message)
      setSubmitting(false)
    }
  }

  function switchMode(next: 'login' | 'signup') {
    setMode(next)
    setError(null)
  }

  return (
    <div className="w-full max-w-md">
      <Link
        href="/"
        className="mb-8 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to playground
      </Link>

      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
        <Logo />

        {/* Toggle */}
        <div className="mt-6 grid grid-cols-2 gap-1 rounded-lg border border-border bg-secondary/60 p-1">
          {(['login', 'signup'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => switchMode(m)}
              className={cn(
                'rounded-md py-1.5 text-sm font-medium transition-colors',
                mode === m
                  ? 'bg-panel text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {m === 'login' ? 'Sign in' : 'Create account'}
            </button>
          ))}
        </div>

        <h1 className="mt-6 font-serif text-2xl font-semibold">
          {mode === 'login' ? 'Welcome back' : 'Start your ledger'}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {mode === 'login'
            ? 'Sign in to see your connected providers and spend advice.'
            : 'Create a free account to connect keys and track spend.'}
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-sm font-medium text-muted-foreground">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="h-11 rounded-lg border border-border bg-panel px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-brand/60 focus:ring-2 focus:ring-brand/20"
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-sm font-medium text-muted-foreground">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="h-11 rounded-lg border border-border bg-panel px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-brand/60 focus:ring-2 focus:ring-brand/20"
              required
            />
          </div>

          {mode === 'signup' && (
            <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {passwordChecks.map((c) => (
                <li
                  key={c.label}
                  className={cn(
                    'flex items-center gap-1.5 text-xs transition-colors',
                    c.ok ? 'text-best' : 'text-muted-foreground',
                  )}
                >
                  {c.ok ? <Check className="size-3.5" /> : <X className="size-3.5 opacity-50" />}
                  {c.label}
                </li>
              ))}
            </ul>
          )}

          {error && (
            <p
              role="alert"
              className="rounded-lg border border-worst/30 bg-worst/10 px-3 py-2.5 text-sm text-worst"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={!canSubmit || submitting}
            className="mt-1 inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-primary text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting && <Loader2 className="size-4 animate-spin" />}
            {mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>
      </div>

      <p className="mt-4 text-center text-xs text-muted-foreground">
        {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
        <button
          type="button"
          onClick={() => switchMode(mode === 'login' ? 'signup' : 'login')}
          className="font-medium text-brand hover:underline"
        >
          {mode === 'login' ? 'Create one' : 'Sign in'}
        </button>
      </p>
    </div>
  )
}
