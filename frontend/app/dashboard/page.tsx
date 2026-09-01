'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { SiteHeader } from '@/components/site-header'
import { KeysPanel } from '@/components/dashboard/keys-panel'
import { AdvisorSection } from '@/components/dashboard/advisor-section'
import { McpKeyGenerator } from '@/components/dashboard/mcp-key-generator'
import { useAuth } from '@/lib/auth-context'

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) router.replace('/auth')
  }, [loading, user, router])

  if (loading || !user) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Loader2 className="size-6 animate-spin text-brand" />
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl px-4 pb-24 pt-8 sm:px-6">
        <div className="flex flex-col gap-1">
          <Link
            href="/"
            className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Back to playground
          </Link>
          <h1 className="mt-3 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            Your ledger
          </h1>
          <p className="text-sm text-muted-foreground">
            Signed in as <span className="font-medium text-foreground">{user.email}</span>
          </p>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-6">
            <KeysPanel />
            <McpKeyGenerator />
          </div>
          <AdvisorSection />
        </div>
      </main>
    </div>
  )
}
