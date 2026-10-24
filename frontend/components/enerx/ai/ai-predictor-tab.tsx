'use client'

import { AlertTriangle, BrainCircuit, Clock, Loader2, Percent, PiggyBank, Zap } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { AI_API_URL, fetchAiForecast } from '@/lib/enerx/ai-api'
import {
  RANGE_DAYS,
  REGIONS,
  REGION_COORDS,
  buildFallbackForecast,
  computeSummary,
  formatMoney,
  fromReport,
  type ForecastResult,
} from '@/lib/enerx/forecast'
import type { ForecastRange, Project, Region } from '@/lib/enerx/types'
import { TOTAL_SUPPLY, formatNumber } from '@/lib/enerx/utils'
import { cn } from '@/lib/utils'
import { Panel, SectionHeader, inputClass, labelClass } from '../primitives'
import { EnergyChart, IrradianceChart, RegionChart, RevenueSplitChart } from './forecast-charts'
import { NewsPanel } from './news-panel'

interface AiPredictorTabProps {
  projects: Project[]
  projectId: string
  region: Region
  range: ForecastRange
  onProjectChange: (id: string) => void
  onRegionChange: (region: Region) => void
  onRangeChange: (range: ForecastRange) => void
}

const RANGES: { id: ForecastRange; label: string }[] = [
  { id: '7d', label: '7 days' },
  { id: '14d', label: '14 days' },
]

type Loaded = { status: 'loading' } | { status: 'ready'; byRegion: Record<Region, ForecastResult>; notice?: string }

/** One AI call per region (cheap) so the regional comparison is real, not simulated. */
function useForecasts(capacityKwp: number, range: ForecastRange): Loaded {
  const [state, setState] = useState<Loaded>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    const days = RANGE_DAYS[range]

    const simulated = (notice?: string): Loaded => ({
      status: 'ready',
      notice,
      byRegion: Object.fromEntries(REGIONS.map((r) => [r, buildFallbackForecast(capacityKwp, r, range)])) as Record<Region, ForecastResult>,
    })

    if (!AI_API_URL) {
      setState(simulated('AI service not configured: showing a simulated estimate.'))
      return
    }
    Promise.all(
      REGIONS.map((r) => fetchAiForecast({ ...REGION_COORDS[r], capacityKw: capacityKwp, days, nTokens: TOTAL_SUPPLY })),
    )
      .then((reports) => {
        if (cancelled) return
        setState({
          status: 'ready',
          byRegion: Object.fromEntries(REGIONS.map((r, i) => [r, fromReport(reports[i])])) as Record<Region, ForecastResult>,
        })
      })
      .catch(() => {
        if (!cancelled) setState(simulated('AI service unreachable: showing a simulated estimate.'))
      })
    return () => {
      cancelled = true
    }
  }, [capacityKwp, range])

  return state
}

export function AiPredictorTab(props: AiPredictorTabProps) {
  const { projects, projectId, region, range } = props
  const project = projects.find((p) => p.id === projectId) ?? projects[0]
  const days = RANGE_DAYS[range]
  const data = useForecasts(project?.capacityKwp ?? 10, range)

  const result = data.status === 'ready' ? data.byRegion[region] : null
  const summary = useMemo(() => (result && project ? computeSummary(result, days, project.targetFunding) : null), [result, days, project])
  const regionData = useMemo(
    () => (data.status === 'ready' ? REGIONS.map((r) => ({ region: r, projected: Math.round(data.byRegion[r].totalKwh) })) : []),
    [data],
  )
  const money = (v: number | undefined, digits = 2) => (result && v !== undefined ? formatMoney(v, result.currency, digits) : '—')

  if (!project) {
    return (
      <div className="enerx-grid-bg">
        <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-10 md:px-6 md:py-14">
          <SectionHeader
            eyebrow="AI predictor · MVP"
            title="No backend project available"
            description="Create a project from the Operate tab after the backend verifies your User identity."
          />
          <Panel className="p-8 text-sm text-slate-400">
            The backend currently returns an empty project list, so no forecast can be attached to a real project yet.
          </Panel>
          <NewsPanel />
        </div>
      </div>
    )
  }

  const kpis = [
    {
      label: 'Projected ROI',
      value: summary?.roiPercent != null ? `${summary.roiPercent.toFixed(1)}%` : '—',
      sub: 'annualized from forecast',
      icon: Percent,
      color: 'text-solar',
    },
    { label: 'Yield / token', value: money(summary?.perTokenYield), sub: 'per year (estimate)', icon: PiggyBank, color: 'text-ledger' },
    {
      label: 'Payback',
      value: summary?.paybackYears != null ? `${summary.paybackYears.toFixed(1)} yrs` : '—',
      sub: 'on target funding',
      icon: Clock,
      color: 'text-azure',
    },
    { label: `Energy · ${days} days`, value: result ? `${formatNumber(result.totalKwh)} kWh` : '—', sub: 'AI production forecast', icon: Zap, color: 'text-violet-400' },
  ]

  return (
    <div className="enerx-grid-bg">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-10 md:px-6 md:py-14">
        <SectionHeader
          eyebrow="AI predictor · production forecast"
          title="Forecast energy & returns"
          description="Revenue is forecast from solar production only (weather → AI model → kWh × provider tariff). Latest energy news are listed for information and never change the numbers."
        />

        <Panel className="flex flex-col gap-4 p-4 md:flex-row md:items-end">
          <div className="md:w-80">
            <label htmlFor="ai-project" className={labelClass}>
              Active project
            </label>
            <select id="ai-project" value={project.id} onChange={(e) => props.onProjectChange(e.target.value)} className={inputClass}>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · {p.capacityKwp} kWp
                </option>
              ))}
            </select>
          </div>
          <div className="md:w-44">
            <label htmlFor="ai-region" className={labelClass}>
              Region
            </label>
            <select id="ai-region" value={region} onChange={(e) => props.onRegionChange(e.target.value as Region)} className={inputClass}>
              {REGIONS.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </div>
          <div className="md:ml-auto">
            <p className={labelClass} id="range-label">
              Horizon
            </p>
            <div role="radiogroup" aria-labelledby="range-label" className="flex rounded-lg border border-white/10 bg-slate-950/70 p-1">
              {RANGES.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  role="radio"
                  aria-checked={range === r.id}
                  onClick={() => props.onRangeChange(r.id)}
                  className={cn(
                    'rounded-md px-3 py-1.5 font-mono text-xs transition',
                    range === r.id ? 'bg-solar text-slate-950 font-semibold' : 'text-slate-400 hover:text-white',
                  )}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
        </Panel>

        {data.status === 'ready' && data.notice && (
          <p className="flex items-center gap-2 rounded-lg border border-amber-400/30 bg-amber-400/5 px-3 py-2 text-xs text-amber-200">
            <AlertTriangle className="size-4 shrink-0" aria-hidden /> {data.notice}
          </p>
        )}

        {!result || !summary ? (
          <Panel className="flex items-center justify-center gap-3 p-16 text-slate-400">
            <Loader2 className="size-5 animate-spin text-solar" aria-hidden />
            <span className="font-mono text-sm">Running the AI model on live weather…</span>
          </Panel>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {kpis.map(({ label, value, sub, icon: Icon, color }) => (
                <Panel key={label} className="p-5">
                  <div className="flex items-center justify-between">
                    <p className="font-mono text-[11px] uppercase tracking-wider text-slate-400">{label}</p>
                    <Icon className={cn('size-4', color)} aria-hidden />
                  </div>
                  <p className={cn('mt-3 text-2xl font-semibold', color)}>{value}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{sub}</p>
                </Panel>
              ))}
            </div>

            <div className="grid gap-5 lg:grid-cols-[1fr_22rem]">
              <Panel className="p-5">
                <ChartHeader title="AI projected energy output (kWh) with 80% range" meta={`${region} · ${formatNumber(result.totalKwh)} kWh over ${days} days`} />
                <EnergyChart data={result.points} />
              </Panel>

              <Panel className="flex flex-col gap-6 p-5">
                <div>
                  <h3 className="flex items-center gap-2 font-semibold text-white">
                    <BrainCircuit className="size-5 text-solar" aria-hidden /> Revenue forecast
                  </h3>
                  <p className="mt-1 text-xs text-slate-400">
                    Production × provider tariff
                    {result.newsCoefficient !== undefined ? ` · news coefficient ${result.newsCoefficient}` : ''}.
                  </p>
                  <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                    Provider tariff: {result.tariffLabel}, matching project funding and distributions.
                  </p>
                </div>
                <dl className="grid grid-cols-2 gap-3">
                  {[
                    { k: 'Provider tariff', v: result.tariffLabel },
                    { k: `Output · ${days} d`, v: `${formatNumber(result.totalKwh)} kWh` },
                    { k: `Owner pool (30%)`, v: money(summary.ownerPool, 0) },
                    { k: `Investor pool (70%)`, v: money(summary.investorPool, 0) },
                  ].map((item) => (
                    <div key={item.k}>
                      <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{item.k}</dt>
                      <dd className="mt-0.5 font-mono text-sm font-semibold text-white">{item.v}</dd>
                    </div>
                  ))}
                </dl>
                <div className="rounded-lg border border-solar/30 bg-solar/5 p-3">
                  <p className="font-mono text-[10px] uppercase tracking-wider text-solar">Annualized revenue (linear estimate)</p>
                  <p className="mt-1 font-mono text-2xl font-semibold text-white">{money(summary.annualRevenue, 0)}</p>
                </div>
                {(result.modelLabel || result.weatherSource || result.generatedAt) && (
                  <p className="border-t border-white/10 pt-4 text-[11px] leading-relaxed text-slate-500">
                    {result.modelLabel && <span className="block">Model: {result.modelLabel}</span>}
                    {result.weatherSource && <span className="block">Weather: {result.weatherSource}</span>}
                    {result.generatedAt && <span className="block">Generated: {new Date(result.generatedAt).toLocaleString()}</span>}
                  </p>
                )}
                {result.reportHash && (
                  <p className="break-all border-t border-white/10 pt-4 font-mono text-[10px] text-slate-500">
                    Report hash (anchorable on Hedera HCS)
                    <br />
                    <span className="text-slate-400">{result.reportHash}</span>
                  </p>
                )}
              </Panel>
            </div>

            {result.warnings.length > 0 && (
              <ul className="space-y-1 rounded-lg border border-white/10 bg-slate-900/50 p-3 text-xs text-slate-400">
                {result.warnings.map((w) => (
                  <li key={w}>⚠ {w}</li>
                ))}
              </ul>
            )}
          </>
        )}

        <NewsPanel />

        {result && (
          <>
            <div className="grid gap-5 lg:grid-cols-2">
              <Panel className="p-5">
                <ChartHeader title="Solar irradiance & temperature" meta="kWh/m²/day · °C" />
                <IrradianceChart data={result.points} />
              </Panel>
              <Panel className="p-5">
                <ChartHeader title="Projected revenue distribution" meta={`Owner 30% · Investors 70% · ${result.currency}`} />
                <RevenueSplitChart data={result.points} unit={result.currency} />
              </Panel>
            </div>

            <Panel className="p-5">
              <ChartHeader title={`Regional output comparison (${days} days)`} meta={`${project.capacityKwp} kWp array`} />
              <RegionChart data={regionData} activeRegion={region} onSelect={props.onRegionChange} />
            </Panel>
          </>
        )}
      </div>
    </div>
  )
}

function ChartHeader({ title, meta }: { title: string; meta: string }) {
  return (
    <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <p className="font-mono text-[11px] text-slate-500">{meta}</p>
    </div>
  )
}
