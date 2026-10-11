import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowLeft, Download, Info, Loader2, Lock } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useSubscription } from '@/hooks/useBilling'
import {
  getErrorMessage,
  indicesApi,
  isUpgradeError,
  UPGRADE_EVENT,
  type AnalyticsPeriod,
  type IndexAnalytics,
} from '@/lib/api'
import { cn, formatDate, formatPercent } from '@/lib/utils'

const PERIODS: Array<{ id: AnalyticsPeriod; years: number }> = [
  { id: '1M', years: 1 / 12 },
  { id: '3M', years: 0.25 },
  { id: '6M', years: 0.5 },
  { id: 'YTD', years: 1 },
  { id: '1Y', years: 1 },
  { id: '3Y', years: 3 },
  { id: '5Y', years: 5 },
  { id: '10Y', years: 10 },
]

const BENCHMARKS = [
  { ticker: 'SPY', label: 'S&P 500 (SPY)' },
  { ticker: 'QQQ', label: 'Nasdaq 100 (QQQ)' },
  { ticker: 'IWM', label: 'Russell 2000 (IWM)' },
  { ticker: 'VT', label: 'Global equities (VT)' },
  { ticker: 'EFA', label: 'Developed ex-US (EFA)' },
  { ticker: 'EEM', label: 'Emerging markets (EEM)' },
]

// Chart colours: categorical slots 1 and 2 of the validated palette. The index
// is always blue and the benchmark always orange, whichever is on screen.
const INDEX_COLOR = '#2a78d6'
const BENCHMARK_COLOR = '#eb6834'
const GRID = '#e1e0d9'
const AXIS = '#898781'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const pct = (value: number | null | undefined, signed = false) =>
  value === null || value === undefined
    ? '–'
    : `${signed && value > 0 ? '+' : ''}${formatPercent(value)}`

const num = (value: number | null | undefined) =>
  value === null || value === undefined ? '–' : value.toFixed(2)

const shortDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })

function Stat({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: 'up' | 'down' }) {
  return (
    <div className="rounded-xl border bg-card p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p
        className={cn(
          'mt-1 text-2xl font-semibold tabular-nums',
          tone === 'up' && 'text-emerald-700',
          tone === 'down' && 'text-red-700'
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  )
}

/** Diverging cell colour: blue for gains, red for losses, neutral at zero. */
function heatColor(value: number): string {
  const strength = Math.min(Math.abs(value) / 0.1, 1)
  if (strength < 0.02) return '#f0efec'
  const alpha = 0.15 + strength * 0.6
  return value > 0 ? `rgba(42, 120, 214, ${alpha})` : `rgba(208, 59, 59, ${alpha})`
}

function MonthlyReturns({ data }: { data: IndexAnalytics['monthly_returns'] }) {
  const years = [...new Set(data.map((m) => m.year))].sort((a, b) => b - a)
  const lookup = new Map(data.map((m) => [`${m.year}-${m.month}`, m.return]))

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr>
            <th className="py-2 pr-3 text-left font-medium text-muted-foreground">Year</th>
            {MONTHS.map((m) => (
              <th key={m} className="px-1 py-2 text-center font-medium text-muted-foreground">{m}</th>
            ))}
            <th className="px-1 py-2 text-center font-medium text-muted-foreground">Total</th>
          </tr>
        </thead>
        <tbody>
          {years.map((year) => {
            const months = MONTHS.map((_, i) => lookup.get(`${year}-${i + 1}`))
            const present = months.filter((v): v is number => v !== undefined)
            // Compounded, not summed: monthly returns chain multiplicatively.
            const total = present.reduce((acc, r) => acc * (1 + r), 1) - 1
            return (
              <tr key={year}>
                <td className="py-1 pr-3 font-medium">{year}</td>
                {months.map((value, i) => (
                  <td key={i} className="p-0.5 text-center">
                    {value === undefined ? (
                      <span className="text-muted-foreground">·</span>
                    ) : (
                      <div
                        className="rounded px-1 py-1.5 text-xs tabular-nums text-foreground"
                        style={{ backgroundColor: heatColor(value) }}
                        title={`${MONTHS[i]} ${year}: ${pct(value, true)}`}
                      >
                        {(value * 100).toFixed(1)}
                      </div>
                    )}
                  </td>
                ))}
                <td className="p-0.5 text-center">
                  <div className="rounded border px-1 py-1.5 text-xs font-semibold tabular-nums">
                    {present.length ? (total * 100).toFixed(1) : '–'}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-muted-foreground">
        Returns in percent. Blue is a gain, red a loss; a partial first or last month covers only the days in range.
      </p>
    </div>
  )
}

export function AnalyticsPage() {
  const { id } = useParams<{ id: string }>()
  const [period, setPeriod] = useState<AnalyticsPeriod>('1Y')
  const [benchmark, setBenchmark] = useState('SPY')
  const [exporting, setExporting] = useState(false)
  const { data: subscription } = useSubscription()
  const maxYears = subscription?.plan.analytics_history_years ?? 1
  const canExport = subscription?.plan.features.includes('data_export') ?? false

  const { data: index, isLoading: indexLoading } = useQuery({
    queryKey: ['index', id],
    queryFn: () => indicesApi.get(id!),
    enabled: !!id,
  })

  const analytics = useQuery({
    queryKey: ['index-analytics', id, period, benchmark],
    queryFn: () => indicesApi.getAnalytics(id!, period, benchmark),
    enabled: !!id,
    placeholderData: keepPreviousData,
    // A plan limit or "no data yet" will not change on retry.
    retry: false,
  })

  const promptUpgrade = (message: string) =>
    window.dispatchEvent(
      new CustomEvent(UPGRADE_EVENT, {
        detail: { code: 'upgrade_required', message, feature: 'extended_history', limit: null, required_plan: 'pro' },
      })
    )

  const handleExport = async () => {
    if (!index) return
    setExporting(true)
    try {
      await indicesApi.exportHistory(id!, index.identifier, period, benchmark)
    } catch (error) {
      if (!isUpgradeError(error)) toast.error('Could not export the history. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  if (indexLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!index) {
    return <div className="py-12 text-center">Index not found</div>
  }

  const data = analytics.data
  const stats = data?.stats
  const benchmarkLabel = data?.benchmark ?? benchmark

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to={`/indices/${id}`} className="mb-2 inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to {index.name}
          </Link>
          <h1 className="text-3xl font-bold">Performance analytics</h1>
          <p className="text-muted-foreground">
            {data
              ? `${formatDate(data.start_date)} to ${formatDate(data.as_of)}, from daily closing prices`
              : 'Performance and risk from daily closing prices'}
          </p>
        </div>
        <Button variant="outline" onClick={handleExport} disabled={!data || exporting}>
          {exporting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : canExport ? (
            <Download className="mr-2 h-4 w-4" />
          ) : (
            <Lock className="mr-2 h-4 w-4" />
          )}
          Export CSV
        </Button>
      </div>

      {/* Filters: one row, above everything they scope */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1 rounded-lg bg-muted p-1" role="tablist" aria-label="Period">
          {PERIODS.map(({ id: p, years }) => {
            const locked = years > maxYears
            return (
              <button
                key={p}
                role="tab"
                aria-selected={period === p}
                onClick={() =>
                  locked
                    ? promptUpgrade('Analytics history beyond one year is available on the Pro plan, with up to 10 years of data.')
                    : setPeriod(p)
                }
                className={cn(
                  'inline-flex items-center gap-1 rounded-md px-3 py-1 text-sm transition-colors',
                  period === p ? 'bg-background text-foreground shadow' : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {p}
                {locked && <Lock className="h-3 w-3" aria-label="Pro" />}
              </button>
            )
          })}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Benchmark</span>
          <select
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value)}
            className="rounded-lg border bg-background px-3 py-1.5"
          >
            {BENCHMARKS.map((b) => (
              <option key={b.ticker} value={b.ticker}>{b.label}</option>
            ))}
          </select>
        </label>
      </div>

      {analytics.isError && !data && (
        <div className="rounded-xl border bg-card p-10 text-center">
          <p className="font-medium">Analytics aren't available for this index yet</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            {getErrorMessage(analytics.error, 'We could not load price history right now.')}
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Button variant="outline" onClick={() => analytics.refetch()}>Try again</Button>
            <Button asChild>
              <Link to={`/indices/${id}`}>Back to index</Link>
            </Button>
          </div>
        </div>
      )}

      {analytics.isLoading && (
        <div className="flex h-64 items-center justify-center rounded-xl border bg-card">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-3 text-sm text-muted-foreground">Loading price history…</span>
        </div>
      )}

      {data && stats && (
        <div className={cn('space-y-6 transition-opacity', analytics.isFetching && 'opacity-60')}>
          {/* What these numbers are, stated once and plainly */}
          <div className="flex items-start gap-3 rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground">
            <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <div className="space-y-1">
              <p>
                This shows how <strong className="text-foreground">today's constituents at today's share counts</strong>{' '}
                performed over the period. It doesn't simulate past rebalances, membership changes or trading costs;{' '}
                <Link to={`/indices/${id}`} className="underline">run a backtest</Link> for that. Past performance is not a guide to future results.
              </p>
              {data.history_truncated && (
                <p>
                  History starts {formatDate(data.start_date)}
                  {data.limited_by ? `, when ${data.limited_by} began trading.` : ', the earliest date every constituent has prices.'}
                </p>
              )}
              {data.excluded_tickers.length > 0 && (
                <p>No price history was found for {data.excluded_tickers.join(', ')}; they are left out of these figures.</p>
              )}
            </div>
          </div>

          {/* Headline figures */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Total return"
              value={pct(stats.total_return, true)}
              tone={stats.total_return === null ? undefined : stats.total_return >= 0 ? 'up' : 'down'}
              hint={
                stats.excess_return !== null
                  ? `${pct(stats.excess_return, true)} vs ${benchmarkLabel}`
                  : 'Benchmark unavailable for this period'
              }
            />
            <Stat label="Volatility" value={pct(stats.volatility)} hint="Annualised, from daily returns" />
            <Stat label="Max drawdown" value={pct(stats.max_drawdown)} hint={`Currently ${pct(stats.current_drawdown)} from peak`} />
            <Stat
              label="Sharpe ratio"
              value={num(stats.sharpe_ratio)}
              hint={stats.sharpe_ratio === null ? 'Needs at least 30 days of history' : 'Annualised return per unit of volatility'}
            />
          </div>

          {/* Level chart */}
          <div className="rounded-xl border bg-card p-6">
            <h2 className="text-lg font-semibold">Index level vs {benchmarkLabel}</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              {data.benchmark ? 'Benchmark rebased to the index level at the start of the period.' : 'Benchmark history was not available for this period.'}
            </p>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.series} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={GRID} vertical={false} />
                  <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={48} tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={{ stroke: GRID }} />
                  <YAxis domain={['auto', 'auto']} width={56} tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => v.toLocaleString('en-US', { maximumFractionDigits: 0 })} />
                  <Tooltip
                    labelFormatter={(label: string) => formatDate(`${label}T00:00:00`)}
                    formatter={(value: number, name: string) => [value.toLocaleString('en-US', { maximumFractionDigits: 2 }), name]}
                    contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
                  />
                  <Legend iconType="plainline" wrapperStyle={{ fontSize: 13 }} />
                  <Line type="monotone" dataKey="value" name={index.identifier} stroke={INDEX_COLOR} strokeWidth={2} dot={false} isAnimationActive={false} />
                  {data.benchmark && (
                    <Line type="monotone" dataKey="benchmark" name={data.benchmark} stroke={BENCHMARK_COLOR} strokeWidth={2} dot={false} isAnimationActive={false} />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Drawdown */}
          <div className="rounded-xl border bg-card p-6">
            <h2 className="text-lg font-semibold">Drawdown</h2>
            <p className="mb-4 text-sm text-muted-foreground">How far the index sat below its previous high on each day.</p>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.series} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={GRID} vertical={false} />
                  <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={48} tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={{ stroke: GRID }} />
                  <YAxis width={56} tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                  <Tooltip
                    labelFormatter={(label: string) => formatDate(`${label}T00:00:00`)}
                    formatter={(value: number) => [formatPercent(value), 'Drawdown']}
                    contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
                  />
                  <Area type="monotone" dataKey="drawdown" stroke={INDEX_COLOR} strokeWidth={2} fill={INDEX_COLOR} fillOpacity={0.15} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="rounded-xl border bg-card p-6">
              <h2 className="mb-3 text-lg font-semibold">Returns</h2>
              {(['1M', '3M', '6M', 'YTD', '1Y', '3Y', '5Y'] as const)
                .filter((p) => p in data.trailing_returns)
                .map((p) => (
                  <Row key={p} label={p === 'YTD' ? 'Year to date' : p} value={pct(data.trailing_returns[p], true)} />
                ))}
              <div className="mt-2 border-t pt-2">
                <Row label="Annualised" value={pct(stats.annualized_return, true)} />
                <Row label="Best day" value={pct(stats.best_day, true)} />
                <Row label="Worst day" value={pct(stats.worst_day, true)} />
                <Row label="Days up" value={pct(stats.positive_days)} />
              </div>
            </div>

            <div className="rounded-xl border bg-card p-6">
              <h2 className="mb-3 text-lg font-semibold">Risk</h2>
              <Row label="Volatility (annualised)" value={pct(stats.volatility)} />
              <Row label="Max drawdown" value={pct(stats.max_drawdown)} />
              <Row label="1-day VaR (95%)" value={pct(stats.var_95)} />
              <Row label="1-day VaR (99%)" value={pct(stats.var_99)} />
              <Row label="Sharpe ratio" value={num(stats.sharpe_ratio)} />
              <Row label="Sortino ratio" value={num(stats.sortino_ratio)} />
              <Row label="Calmar ratio" value={num(stats.calmar_ratio)} />
              <p className="mt-3 text-xs text-muted-foreground">
                VaR is historical: the daily loss exceeded on 5% (or 1%) of days in this period. Ratios use a 0% risk-free rate.
              </p>
            </div>

            <div className="rounded-xl border bg-card p-6">
              <h2 className="mb-3 text-lg font-semibold">Against {benchmarkLabel}</h2>
              <Row label={`${benchmarkLabel} return`} value={pct(stats.benchmark_total_return, true)} />
              <Row label="Excess return" value={pct(stats.excess_return, true)} />
              <Row label="Beta" value={num(stats.beta)} />
              <Row label="Correlation" value={num(stats.correlation)} />
              <Row label="Tracking error" value={pct(stats.tracking_error)} />
              <Row label="Information ratio" value={num(stats.information_ratio)} />
              <Row label={`${benchmarkLabel} volatility`} value={pct(stats.benchmark_volatility)} />
            </div>
          </div>

          {data.monthly_returns.length > 1 && (
            <div className="rounded-xl border bg-card p-6">
              <h2 className="mb-4 text-lg font-semibold">Monthly returns</h2>
              <MonthlyReturns data={data.monthly_returns} />
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border bg-card p-6">
              <h2 className="mb-4 text-lg font-semibold">Sector allocation</h2>
              <div className="space-y-3">
                {data.sector_allocation.map((sector) => (
                  <div key={sector.name}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span>{sector.name}</span>
                      <span className="font-medium tabular-nums">{formatPercent(sector.weight)}</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${Math.min(sector.weight, 1) * 100}%`, backgroundColor: INDEX_COLOR }}
                      />
                    </div>
                  </div>
                ))}
                {data.sector_allocation.length === 0 && (
                  <p className="text-sm text-muted-foreground">No weights yet. Calculate the index to see its allocation.</p>
                )}
              </div>
            </div>

            <div className="rounded-xl border bg-card p-6">
              <h2 className="mb-3 text-lg font-semibold">Concentration</h2>
              <Row label="Constituents" value={String(data.concentration.count)} />
              <Row label="Top 5 weight" value={pct(data.concentration.top_5_weight)} />
              <Row label="Top 10 weight" value={pct(data.concentration.top_10_weight)} />
              <Row
                label="Effective holdings"
                value={data.concentration.effective_holdings === null ? '–' : data.concentration.effective_holdings.toFixed(1)}
              />
              <p className="mt-3 text-xs text-muted-foreground">
                Effective holdings is the number of equally weighted stocks that would be as concentrated as this index.
                A value well below the constituent count means a few names dominate.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
