import Link from 'next/link'
import { ArrowRight, Zap, KeyRound, LineChart, Activity } from 'lucide-react'
import { SiteHeader } from '@/components/site-header'
import { CostPlayground } from '@/components/playground/cost-playground'
import { TickerTape } from '@/components/ticker-tape'

export default function Page() {
  return (
    <div className="min-h-screen">
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl px-4 pb-24 sm:px-6">
        {/* Hero */}
        <section className="relative">
          <div
            aria-hidden="true"
            className="grid-texture pointer-events-none absolute inset-x-0 -top-14 h-[420px]"
            style={{
              maskImage: 'radial-gradient(120% 60% at 50% 0%, black, transparent)',
              WebkitMaskImage: 'radial-gradient(120% 60% at 50% 0%, black, transparent)',
            }}
          />
          <div className="relative pt-12 pb-8 sm:pt-16">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-brand/30 bg-brand/10 px-3 py-1 text-xs font-medium text-brand">
                <Activity className="size-3.5" />
                Live pricing across 8 models
              </span>
            </div>
            <h1 className="mt-5 max-w-3xl text-balance font-serif text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl md:text-6xl">
              Watch your prompt&apos;s price move across every model, live.
            </h1>
            <p className="mt-4 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
              Ledger prices any prompt against OpenAI, Anthropic, and Groq in real time, like a
              trading ticker for AI spend. OpenAI runs instantly with a local tokenizer, so
              there&apos;s nothing to set up.
            </p>
          </div>

          {/* Signature element: scrolling price ticker */}
          <div className="relative mb-8">
            <TickerTape />
          </div>
        </section>

        {/* Playground hero */}
        <section className="rounded-2xl border border-border bg-card/50 p-4 shadow-[0_1px_0_0_rgba(232,230,223,0.04)_inset] sm:p-6">
          <CostPlayground />
        </section>

        {/* Subtle sign-in prompt */}
        <section className="mt-6 flex flex-col items-start justify-between gap-4 overflow-hidden rounded-xl border border-brand/25 bg-gradient-to-br from-brand/[0.07] to-transparent px-5 py-5 sm:flex-row sm:items-center">
          <div>
            <p className="font-serif text-lg font-medium">Want the full ledger?</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Connect your own Anthropic and Groq keys, track spend over time, and get AI-written
              savings advice.
            </p>
          </div>
          <Link
            href="/auth?mode=signup"
            className="group inline-flex shrink-0 items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
          >
            Create a free account
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </section>

        {/* Feature strip */}
        <section className="mt-14">
          <div className="flex items-center gap-3">
            <h2 className="font-serif text-2xl font-semibold">How it works</h2>
            <div className="h-px flex-1 bg-border" />
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <Feature
              step="01"
              icon={<Zap className="size-5 text-brand" />}
              title="Instant OpenAI pricing"
              body="A local tokenizer prices gpt-4o and gpt-4o-mini as you type. No waiting on a round trip."
            />
            <Feature
              step="02"
              icon={<KeyRound className="size-5 text-brand" />}
              title="Bring your own keys"
              body="Connect the regular API keys you already use in code to unlock Anthropic and Groq rows."
            />
            <Feature
              step="03"
              icon={<LineChart className="size-5 text-brand" />}
              title="Advice, not just numbers"
              body="The Advisor reads your usage patterns and recommends where to cut spend, in plain English."
            />
          </div>
        </section>
      </main>

      <footer className="border-t border-border/70">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 text-xs text-muted-foreground sm:flex-row sm:px-6">
          <p>Ledger, an interactive AI cost playground.</p>
          <p className="font-mono">prices are estimates · verify against provider billing</p>
        </div>
      </footer>
    </div>
  )
}

function Feature({
  step,
  icon,
  title,
  body,
}: {
  step: string
  icon: React.ReactNode
  title: string
  body: string
}) {
  return (
    <div className="group relative rounded-xl border border-border bg-panel/50 p-5 transition-colors hover:border-brand/40">
      <div className="flex items-center justify-between">
        <div className="grid size-10 place-items-center rounded-lg border border-border bg-secondary transition-colors group-hover:border-brand/40">
          {icon}
        </div>
        <span className="font-mono text-xs tabular-nums text-muted-foreground/60">{step}</span>
      </div>
      <h3 className="mt-4 font-serif text-base font-semibold">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{body}</p>
    </div>
  )
}
