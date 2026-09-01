export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') || 'http://localhost:8000'

export const TOKEN_KEY = 'ledger_token'

export type Provider = 'openai' | 'anthropic' | 'groq'

export interface ModelSpec {
  provider: Provider
  model: string
  label: string
  /** OpenAI works with no key via a local tokenizer. Others require a connected key. */
  requiresKey: boolean
}

/** Models shown on the leaderboard, in a stable default order. */
export const MODELS: ModelSpec[] = [
  { provider: 'openai', model: 'gpt-4o', label: 'GPT-4o', requiresKey: false },
  { provider: 'openai', model: 'gpt-4o-mini', label: 'GPT-4o mini', requiresKey: false },
  { provider: 'anthropic', model: 'claude-opus-5', label: 'Claude Opus 5', requiresKey: true },
  { provider: 'anthropic', model: 'claude-sonnet-5', label: 'Claude Sonnet 5', requiresKey: true },
  { provider: 'anthropic', model: 'claude-haiku-4-5', label: 'Claude Haiku 4.5', requiresKey: true },
{ provider: 'groq', model: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B', requiresKey: false },
{ provider: 'groq', model: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B', requiresKey: false },
]

export const PROVIDER_LABELS: Record<Provider, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  groq: 'Groq',
}

/** Shape returned by POST /usage/log. Fields are optional to stay resilient to the backend. */
export interface UsageLogResponse {
  cost_usd?: number
  cost?: number
  total_cost?: number
  input_cost?: number
  output_cost?: number
  input_tokens?: number
  output_tokens?: number
  prompt_tokens?: number
  fits_context_window?: boolean
  context_window?: number
  approximate?: boolean
  [key: string]: unknown
}
export interface AuthUser {
  id?: string | number
  email: string
  [key: string]: unknown
}

export interface ConnectedKey {
  id: string | number
  provider: Provider | string
  label?: string
  created_at?: string
  last_four?: string
  [key: string]: unknown
}

export interface AdvisorResponse {
  pattern: Record<string, unknown>
  recommendation: string
}

export interface McpKeyResponse {
  raw_key: string
  [key: string]: unknown
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

/**
 * Normalizes FastAPI error payloads. `detail` can be a string OR an array of
 * `{ msg }` objects (validation errors). Returns a single human-readable string.
 */
function parseErrorDetail(data: unknown, fallback: string): string {
  if (!data || typeof data !== 'object') return fallback
  const detail = (data as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => {
        if (typeof d === 'string') return d
        if (d && typeof d === 'object' && 'msg' in d) return String((d as { msg: unknown }).msg)
        return null
      })
      .filter(Boolean)
    if (messages.length) return messages.join('. ')
  }
  return fallback
}

interface RequestOptions {
  method?: string
  body?: unknown
  token?: string | null
  signal?: AbortSignal
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, token, signal } = options
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    })
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err
    throw new ApiError(
      `Could not reach the API at ${API_BASE}. Is the backend running?`,
      0,
    )
  }

  let data: unknown = null
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!res.ok) {
    throw new ApiError(
      parseErrorDetail(data, `Request failed (${res.status})`),
      res.status,
    )
  }

  return data as T
}

/** Best-effort extraction of a single cost number from a usage log response. */
export function extractCost(r: UsageLogResponse): number | null {
  const candidates = [r.cost_usd, r.total_cost, r.cost]
  for (const c of candidates) {
    if (typeof c === 'number' && !Number.isNaN(c)) return c
  }
  if (typeof r.input_cost === 'number' && typeof r.output_cost === 'number') {
    return r.input_cost + r.output_cost
  }
  return null
}

/** Formats a USD cost with adaptive precision so tiny values remain legible. */
export function formatCost(value: number): string {
  if (value === 0) return '$0.00'
  if (value < 0.01) return `$${value.toFixed(6)}`
  if (value < 1) return `$${value.toFixed(4)}`
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatTokens(value: number): string {
  return value.toLocaleString('en-US')
}
