import type { NewsItem } from './news'

/** Backend model routes are the primary AI service; a separate service may override them. */
export const AI_API_URL = (
  process.env.NEXT_PUBLIC_AI_API_URL ??
  `${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/model`
).replace(/\/$/, '')

export interface AiDay {
  date: string
  temperature_c: number
  irradiance_wh_m2: number
  kwh: number
  kwh_low: number
  kwh_high: number
  revenue_dt: number
  dividend_per_token_dt: number
  dividend_per_token_low_dt?: number
  dividend_per_token_high_dt?: number
  revenue_usdc?: number
  dividend_per_token_usdc?: number
  dividend_per_token_low_usdc?: number
  dividend_per_token_high_usdc?: number
}

export interface AiReport {
  generated_at?: string
  location?: { lat: number; lon: number }
  capacity_kw: number
  assumptions: {
    tariff_dt_per_kwh: number
    n_tokens: number
    news_coefficient?: number
    weather_source?: string
    model?: string
    fx?: { from: string; to: string; rate: number; source?: string; date?: string; status: string }
  }
  days: AiDay[]
  totals: {
    kwh: number
    revenue_dt: number
    dividend_per_token_dt?: number
    revenue_usdc?: number
    dividend_per_token_usdc?: number
  }
  warnings?: string[]
  report_hash: string
}

interface AiNewsItem {
  title: string
  source?: string
  url?: string
  date?: string | null
  summary?: string
  category?: string
  justification?: string
}

interface RawAiNewsResponse {
  items?: AiNewsItem[]
  headlines?: AiNewsItem[]
  origin?: string
  refreshing?: boolean
  informational_only?: boolean
}

export interface AiNewsResponse {
  items: NewsItem[]
  origin?: string
  refreshing?: boolean
  informational_only?: boolean
}

async function aiGet<T>(path: string, timeoutMs: number): Promise<T> {
  if (!AI_API_URL) throw new Error('NEXT_PUBLIC_AI_API_URL not set')
  const res = await fetch(`${AI_API_URL}${path}`, { cache: 'no-store', signal: AbortSignal.timeout(timeoutMs) })
  if (!res.ok) throw new Error(`AI service ${res.status}`)
  return (await res.json()) as T
}

export function fetchAiForecast(p: { lat: number; lon: number; capacityKw: number; days: number; nTokens: number }) {
  const q = new URLSearchParams({
    lat: String(p.lat),
    lon: String(p.lon),
    capacity_kw: String(p.capacityKw),
    days: String(p.days),
    n_tokens: String(p.nTokens),
  })
  return aiGet<AiReport>(`/forecast?${q}`, 45_000)
}

export async function fetchAiNews(): Promise<AiNewsResponse> {
  const data = await aiGet<RawAiNewsResponse>('/news', 10_000)
  const items = data.items ?? data.headlines ?? []
  return {
    ...data,
    items: items.map((n, i) => ({
      id: `ai-${i}-${n.url ?? n.title}`,
      title: n.title,
      source: n.source ?? 'EnerX AI',
      url: n.url ?? `${AI_API_URL}/news`,
      summary: n.summary ?? n.justification,
      publishedAt: n.date ? new Date(n.date).toISOString() : null,
    })),
  }
}
