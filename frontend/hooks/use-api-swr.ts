'use client'

import useSWR, { type SWRConfiguration } from 'swr'
import { apiRequest } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

/**
 * Authenticated SWR wrapper. The key is `null` (paused) until a token exists,
 * so protected endpoints are never called anonymously.
 */
export function useApiSWR<T>(path: string | null, config?: SWRConfiguration<T>) {
  const { token } = useAuth()
  return useSWR<T>(
    token && path ? [path, token] : null,
    ([p, t]: [string, string]) => apiRequest<T>(p, { token: t }),
    config,
  )
}
