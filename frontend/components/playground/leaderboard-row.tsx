'use client'

import Link from 'next/link'
import { motion } from 'motion/react'
import { Lock, TrendingUp, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  formatCost,
  formatTokens,
  PROVIDER_LABELS,
  type Provider,
} from '@/lib/api'

export type RowStatus = 'idle' | 'loading' | 'ok' | 'locked' | 'error' | 'unfit'
export type Tier = 'best' | 'mid' | 'worst' | null

export interface RowData {
  key: string
  provider: Provider
  label: string
  model: string
  status: RowStatus
  cost: number | null
  inputTokens: number | null
  outputTokens: number | null
  contextWindow: number | null
  error: string | null
}

const TIER_STYLES: Record<'best' | 'mid' | 'worst', { text: string; dot: string; bar: string }> = {
  best: { text: 'text-best', dot: 'bg-best', bar: 'bg-best/70' },
  mid: { text: 'text-mid', dot: 'bg-mid', bar: 'bg-mid/70' },
  worst: { text: 'text-worst', dot: 'bg-worst', bar: 'bg-worst/70' },
}

interface Props {
  row: RowData
  rank: number | null
  tier: Tier
  /** Cost as a fraction (0-1) of the most expensive computed model, for the bar width. */
  ratio: number
}

export function LeaderboardRow({ row, rank, tier, ratio }: Props) {
  const isLocked = row.status === 'locked'
  const isUnfit = row.status === 'unfit'
  const isLoading = row.status === 'loading'
  const isError = row.status === 'error'
  const tierStyle = tier ? TIER_STYLES[tier] : null

  return (
    <motion.li
      layout
      transition={{ type: 'spring', stiffness: 420, damping: 34 }}
      className={cn(
        'relative overflow-hidden rounded-lg border border-border bg-panel px-3 py-3 sm:px-4',
        isUnfit && 'opacity-60',
        tier === 'best' && 'border-best/40 shadow-[0_0_0_1px_rgba(52,211,153,0.15)]',
      )}
    >
      {/* subtle cost bar behind content */}
      {row.status === 'ok' && tierStyle && (
        <motion.div
          aria-hidden="true"
          layout="position"
          className={cn('absolute inset-y-0 left-0 opacity-[0.07]', tierStyle.bar)}
          style={{ width: `${Math.max(6, ratio * 100)}%` }}
        />
      )}

      <div className="relative flex items-center gap-3">
        <div className="flex w-6 shrink-0 items-center justify-center">
          {rank !== null ? (
            <span
              className={cn(
                'font-mono text-xs tabular-nums',
                tierStyle ? tierStyle.text : 'text-muted-foreground',
              )}
            >
              {rank}
            </span>
          ) : (
            <span className={cn('size-2 rounded-full', isLocked ? 'bg-muted-foreground/40' : 'bg-muted-foreground/60')} />
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={cn('truncate text-sm font-medium', isLocked && 'blur-[3px] select-none')}>
              {row.label}
            </span>
            {tier === 'best' && (
              <span className="inline-flex items-center gap-1 rounded-full bg-best/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-best">
                <TrendingUp className="size-3" />
                Best value
              </span>
            )}
            {isUnfit && (
              <span className="inline-flex items-center gap-1 rounded-full bg-worst/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-worst">
                <AlertTriangle className="size-3" />
                Over context
              </span>
            )}
          </div>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
            <span className={cn(isLocked && 'blur-[3px] select-none')}>{PROVIDER_LABELS[row.provider]}</span>
            {row.status === 'ok' && row.inputTokens !== null && (
              <span className="font-mono tabular-nums">
                {formatTokens(row.inputTokens)} in
                {row.outputTokens !== null ? ` · ${formatTokens(row.outputTokens)} out` : ''}
              </span>
            )}
            {isUnfit && row.contextWindow !== null && (
              <span className="font-mono tabular-nums text-worst/80">
                exceeds {formatTokens(row.contextWindow)} ctx
              </span>
            )}
            {isError && <span className="text-worst/80">{row.error ?? 'Failed to price'}</span>}
          </div>
        </div>

        {/* right column: cost / lock / spinner */}
        <div className="flex shrink-0 items-center justify-end">
          {isLocked ? (
            <Link
              href="/auth?mode=signup"
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-brand/50 hover:text-foreground"
            >
              <Lock className="size-3 text-brand" />
              Connect key
            </Link>
          ) : isLoading ? (
            <span className="font-mono text-sm tabular-nums text-muted-foreground">
              <span className="inline-block animate-pulse">calculating…</span>
            </span>
          ) : row.status === 'ok' && row.cost !== null ? (
            <span
              className={cn(
                'font-mono text-base font-semibold tabular-nums sm:text-lg',
                tierStyle ? tierStyle.text : 'text-foreground',
              )}
            >
              {formatCost(row.cost)}
            </span>
          ) : isUnfit ? (
            <span className="font-mono text-sm tabular-nums text-worst">n/a</span>
          ) : (
            <span className="font-mono text-sm tabular-nums text-muted-foreground">···</span>
          )}
        </div>
      </div>
    </motion.li>
  )
}
