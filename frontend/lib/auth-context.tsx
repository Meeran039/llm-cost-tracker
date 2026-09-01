'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { apiRequest, TOKEN_KEY, type AuthUser } from '@/lib/api'

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  /** True until the initial session-restore attempt finishes. */
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore session from localStorage on mount.
  useEffect(() => {
    const stored = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
    if (!stored) {
      setLoading(false)
      return
    }
    let cancelled = false
    apiRequest<AuthUser>('/auth/me', { token: stored })
      .then((me) => {
        if (cancelled) return
        setToken(stored)
        setUser(me)
      })
      .catch(() => {
        if (cancelled) return
        localStorage.removeItem(TOKEN_KEY)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const applyToken = useCallback(async (accessToken: string) => {
    localStorage.setItem(TOKEN_KEY, accessToken)
    const me = await apiRequest<AuthUser>('/auth/me', { token: accessToken })
    setToken(accessToken)
    setUser(me)
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await apiRequest<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: { email, password },
      })
      await applyToken(res.access_token)
    },
    [applyToken],
  )

  const signup = useCallback(
    async (email: string, password: string) => {
      await apiRequest('/auth/signup', {
        method: 'POST',
        body: { email, password },
      })
      // Sign in immediately after a successful signup.
      const res = await apiRequest<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: { email, password },
      })
      await applyToken(res.access_token)
    },
    [applyToken],
  )

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, token, loading, login, signup, logout }),
    [user, token, loading, login, signup, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
