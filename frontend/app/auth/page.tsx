import { Suspense } from 'react'
import { AuthForm } from '@/components/auth/auth-form'

export default function AuthPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_50%_-10%,rgba(201,162,39,0.10),transparent_55%)]"
      />
      <Suspense fallback={<div className="h-10 w-10 animate-pulse rounded-full bg-muted" />}>
        <AuthForm />
      </Suspense>
    </main>
  )
}
