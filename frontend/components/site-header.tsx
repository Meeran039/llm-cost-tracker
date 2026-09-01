'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { LayoutDashboard, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/logo'
import { useAuth } from '@/lib/auth-context'

export function SiteHeader() {
  const { user, logout, loading } = useAuth()
  const router = useRouter()

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" aria-label="Ledger home">
          <Logo />
        </Link>

        <nav className="flex items-center gap-2">
          {loading ? (
            <div className="h-7 w-20 animate-pulse rounded-md bg-muted" aria-hidden="true" />
          ) : user ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                nativeButton={false}
                render={<Link href="/dashboard" />}
              >
                <LayoutDashboard />
                <span className="hidden sm:inline">Dashboard</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  logout()
                  router.push('/')
                }}
              >
                <LogOut />
                <span className="hidden sm:inline">Sign out</span>
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="ghost"
                size="sm"
                nativeButton={false}
                render={<Link href="/auth" />}
              >
                Sign in
              </Button>
              <Button size="sm" nativeButton={false} render={<Link href="/auth?mode=signup" />}>
                Get started
              </Button>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
