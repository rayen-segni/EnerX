import type { AiReport } from './ai-api'
import type { ForecastRange, Region } from './types'
import { OWNER_RETAINED, TOTAL_SUPPLY } from './utils'

export const REGIONS: Region[] = ['Tunis', 'Sfax', 'Tozeur', 'Djerba']

/** Position sent to the AI model for each region (city centres). */
export const REGION_COORDS: Record<Region, { lat: number; lon: number }> = {
  Tunis: { lat: 36.8, lon: 10.18 },
  Sfax: { lat: 34.74, lon: 10.76 },
  Tozeur: { lat: 33.92, lon: 8.13 },
  Djerba: { lat: 33.81, lon: 10.86 },
}

export const RANGE_DAYS: Record<ForecastRange, number> = { '7d': 7, '14d': 14 }

/** Revenue depends only on forecast production x provider tariff. News never enter the calculation. */
export const OWNER_SHARE = OWNER_RETAINED / TOTAL_SUPPLY

/**
 * Provider-set energy price used by the demo.
 * It is denominated in the same unit as project funding: USDT.
 * Configure NEXT_PUBLIC_PROVIDER_TARIFF_USDT_PER_KWH for a different provider contract.
 */
const configuredProviderTariff = Number(process.env.NEXT_PUBLIC_PROVIDER_TARIFF_USDT_PER_KWH ?? '0.25')
export const PROVIDER_TARIFF_USDT_PER_KWH =
  Number.isFinite(configuredProviderTariff) && configuredProviderTariff > 0 ? configuredProviderTariff : 0.25

export type Currency = 'USDT'

export interface ForecastPoint {
  label: string
  temperature: number
  irradiance: number // kWh/m²/day
  projected: number // kWh
  low: number
  high: number
  ownerRevenue: number
  investorRevenue: number
}

export interface ForecastResult {
  points: ForecastPoint[]
  currency: Currency
  totalKwh: number
  totalRevenue: number
  tariffLabel: string
  reportHash?: string
  generatedAt?: string
  modelLabel?: string
  weatherSource?: string
  newsCoefficient?: number
  warnings: string[]
  source: 'model' | 'simulated'
}

export function fromReport(report: AiReport): ForecastResult {
  const totalKwh = report.totals.kwh
  const points = report.days.map((d) => {
    const revenue = d.kwh * PROVIDER_TARIFF_USDT_PER_KWH
    return {
      label: d.date.slice(5),
      temperature: d.temperature_c,
      irradiance: Number((d.irradiance_wh_m2 / 1000).toFixed(2)),
      projected: Math.round(d.kwh),
      low: Math.round(d.kwh_low),
      high: Math.round(d.kwh_high),
      ownerRevenue: Number((revenue * OWNER_SHARE).toFixed(2)),
      investorRevenue: Number((revenue * (1 - OWNER_SHARE)).toFixed(2)),
    }
  })
  return {
    points,
    currency: 'USDT',
    totalKwh,
    totalRevenue: totalKwh * PROVIDER_TARIFF_USDT_PER_KWH,
    tariffLabel: `${PROVIDER_TARIFF_USDT_PER_KWH.toFixed(3)} USDT/kWh`,
    reportHash: report.report_hash,
    generatedAt: report.generated_at,
    modelLabel: report.assumptions.model,
    weatherSource: report.assumptions.weather_source,
    newsCoefficient: report.assumptions.news_coefficient,
    warnings: report.warnings ?? [],
    source: 'model',
  }
}

// ---------------------------------------------------------------------------
// Offline fallback (used only when the AI service cannot be reached)
// ---------------------------------------------------------------------------
const REGION_PROFILE: Record<Region, { yield: number; cloud: number }> = {
  Tunis: { yield: 1, cloud: 34 },
  Sfax: { yield: 1.08, cloud: 26 },
  Tozeur: { yield: 1.22, cloud: 11 },
  Djerba: { yield: 1.13, cloud: 21 },
}
const noise = (i: number, seed: number) => {
  const x = Math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
  return x - Math.floor(x)
}

export function buildFallbackForecast(capacityKwp: number, region: Region, range: ForecastRange): ForecastResult {
  const profile = REGION_PROFILE[region]
  const seed = REGIONS.indexOf(region) * 13 + capacityKwp
  const today = new Date()
  const pointsWithoutRevenue = Array.from({ length: RANGE_DAYS[range] }, (_, i) => {
    const cloud = Math.min(88, Math.max(2, profile.cloud * (0.45 + noise(i, seed) * 1.1)))
    const projected = capacityKwp * 0.62 * profile.yield * 0.88 * (1 - cloud / 220) * 8
    const d = new Date(today.getTime() + i * 86_400_000)
    return {
      label: d.toISOString().slice(5, 10),
      temperature: Number((22 + noise(i, seed + 3) * 8).toFixed(1)),
      irradiance: Number((6.4 * profile.yield * 0.88 * (1 - cloud / 160)).toFixed(2)),
      projected: Math.round(projected),
      low: Math.round(projected * 0.88),
      high: Math.round(projected * 1.12),
    }
  })
  const totalKwh = pointsWithoutRevenue.reduce((s, p) => s + p.projected, 0)
  const tariff = PROVIDER_TARIFF_USDT_PER_KWH
  const points = pointsWithoutRevenue.map((point) => {
    const revenue = point.projected * tariff
    return {
      ...point,
      ownerRevenue: Number((revenue * OWNER_SHARE).toFixed(2)),
      investorRevenue: Number((revenue * (1 - OWNER_SHARE)).toFixed(2)),
    }
  })
  return {
    points,
    currency: 'USDT',
    totalKwh,
    totalRevenue: points.reduce((s, p) => s + p.ownerRevenue + p.investorRevenue, 0),
    tariffLabel: `${tariff.toFixed(3)} USDT/kWh`,
    warnings: [],
    source: 'simulated',
  }
}

// ---------------------------------------------------------------------------
// Return metrics (linear annualisation of the forecast window)
// ---------------------------------------------------------------------------
export function computeSummary(result: ForecastResult, days: number, targetFunding: number) {
  const annualRevenue = (result.totalRevenue / days) * 365
  return {
    annualRevenue,
    roiPercent: (annualRevenue / targetFunding) * 100,
    perTokenYield: annualRevenue / TOTAL_SUPPLY,
    paybackYears: annualRevenue > 0 ? targetFunding / annualRevenue / 3 : null,
    ownerPool: result.totalRevenue * OWNER_SHARE,
    investorPool: result.totalRevenue * (1 - OWNER_SHARE),
  }
}

export function formatMoney(value: number, currency: Currency, digits = 2) {
  const n = new Intl.NumberFormat('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value)
  return `${n} ${currency}`
}
