import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span
        aria-hidden="true"
        className="grid size-7 place-items-center rounded-md border border-brand/40 bg-brand/10"
      >
        <svg viewBox="0 0 24 24" className="size-4 text-brand" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M4 5h16M4 12h16M4 19h10" strokeLinecap="round" />
          <circle cx="19" cy="19" r="2" fill="currentColor" stroke="none" />
        </svg>
      </span>
      <span className="font-serif text-lg font-semibold tracking-tight text-foreground">
        Ledger
      </span>
    </span>
  )
}
