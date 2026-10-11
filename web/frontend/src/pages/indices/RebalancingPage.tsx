import { useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, RefreshCw, AlertTriangle, Download, Loader2, Lock, CheckCircle } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useSubscription } from '@/hooks/useBilling'
import { getErrorMessage, indicesApi, UPGRADE_EVENT } from '@/lib/api'
import { cn, formatCurrency, formatDate, formatPercent } from '@/lib/utils'

type Action = 'BUY' | 'SELL' | 'HOLD'

interface TradeRow {
  ticker: string
  name: string
  price: number | null
  currentWeight: number
  targetWeight: number
  drift: number
  action: Action
  tradeValue: number
  shares: number | null
}

const FREQUENCY_LABELS: Record<string, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  semi_annual: 'Semi-annual',
  annual: 'Annual',
}

/** Signed drift; anything that rounds to zero is shown as plain 0.00%, never "-0.00%". */
const formatDrift = (drift: number) =>
  Math.abs(drift) < 0.00005 ? formatPercent(0) : `${drift > 0 ? '+' : ''}${formatPercent(drift)}`

const csvCell = (value: string) => `"${value.replace(/"/g, '""')}"`

export function RebalancingPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [driftThreshold, setDriftThreshold] = useState(0.01)
  const [portfolioValue, setPortfolioValue] = useState(1_000_000)
  const { data: subscription } = useSubscription()
  const canExport = subscription?.plan.features.includes('data_export') ?? false

  const { data: index, isLoading: indexLoading } = useQuery({
    queryKey: ['index', id],
    queryFn: () => indicesApi.get(id!),
    enabled: !!id,
  })

  const preview = useQuery({
    queryKey: ['rebalance-preview', id],
    queryFn: () => indicesApi.rebalancePreview(id!),
    enabled: !!id,
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['index', id] })
    queryClient.invalidateQueries({ queryKey: ['rebalance-preview', id] })
    queryClient.invalidateQueries({ queryKey: ['index-analytics', id] })
  }

  const repriceMutation = useMutation({
    mutationFn: () => indicesApi.calculate(id!),
    onSuccess: () => {
      refresh()
      toast.success('Prices refreshed')
    },
    onError: (error) => toast.error(getErrorMessage(error, 'Could not refresh prices.')),
  })

  const rebalanceMutation = useMutation({
    mutationFn: () => indicesApi.rebalance(id!),
    onSuccess: () => {
      refresh()
      setShowConfirmDialog(false)
      toast.success('Index rebalanced to target weights')
    },
    onError: (error) => {
      setShowConfirmDialog(false)
      toast.error(getErrorMessage(error, 'Rebalance failed. Nothing was changed.'))
    },
  })

  // Trades for a portfolio of the given size tracking this index. Drift is real:
  // current weights come from the last pricing, targets from the methodology.
  const rows = useMemo<TradeRow[]>(() => {
    if (!preview.data) return []
    return preview.data.components.map((c) => {
      const action: Action = Math.abs(c.drift) < driftThreshold ? 'HOLD' : c.drift > 0 ? 'SELL' : 'BUY'
      const tradeValue = Math.abs(c.drift) * portfolioValue
      return {
        ticker: c.ticker,
        name: c.name || c.ticker,
        price: c.price,
        currentWeight: c.current_weight,
        targetWeight: c.target_weight,
        drift: c.drift,
        action,
        tradeValue,
        shares: c.price && c.price > 0 ? tradeValue / c.price : null,
      }
    })
  }, [preview.data, driftThreshold, portfolioValue])

  const stats = useMemo(() => {
    const trades = rows.filter((r) => r.action !== 'HOLD')
    const traded = trades.reduce((sum, r) => sum + r.tradeValue, 0)
    return {
      trades: trades.length,
      buys: trades.filter((r) => r.action === 'BUY').length,
      sells: trades.filter((r) => r.action === 'SELL').length,
      // One-way: buys and sells are two sides of the same reallocation.
      turnover: portfolioValue > 0 ? traded / 2 / portfolioValue : 0,
    }
  }, [rows, portfolioValue])

  const exportTradeList = () => {
    if (!canExport) {
      window.dispatchEvent(
        new CustomEvent(UPGRADE_EVENT, {
          detail: {
            code: 'upgrade_required',
            message: 'Exporting trade lists as CSV is available on the Pro plan.',
            feature: 'data_export',
            limit: null,
            required_plan: 'pro',
          },
        })
      )
      return
    }
    const lines = [
      'Ticker,Name,Action,Current Weight,Target Weight,Drift,Price,Trade Value,Shares',
      ...rows
        .filter((r) => r.action !== 'HOLD')
        .map((r) =>
          [
            r.ticker,
            csvCell(r.name),
            r.action,
            r.currentWeight.toFixed(6),
            r.targetWeight.toFixed(6),
            r.drift.toFixed(6),
            r.price ?? '',
            r.tradeValue.toFixed(2),
            r.shares === null ? '' : r.shares.toFixed(4),
          ].join(',')
        ),
    ]
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `${index?.identifier || 'index'}_rebalance_trades.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (indexLoading || preview.isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!index) {
    return <div className="py-12 text-center">Index not found</div>
  }

  if (preview.isError || !preview.data) {
    return (
      <div className="py-12 text-center">
        <p className="font-medium">Couldn't load the rebalance preview</p>
        <Button variant="outline" className="mt-4" onClick={() => preview.refetch()}>
          Try again
        </Button>
      </div>
    )
  }

  const data = preview.data
  const unpriced = data.components.filter((c) => !c.priced)
  const maxWeight = Math.max(...rows.map((r) => Math.max(r.currentWeight, r.targetWeight)), 0.01)
  const inBalance = data.max_drift < 0.0005

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to={`/indices/${id}`} className="mb-2 inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to {index.name}
          </Link>
          <h1 className="text-3xl font-bold">Rebalancing</h1>
          <p className="text-muted-foreground">
            How far current weights have drifted from target, and the trades that would close the gap
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => repriceMutation.mutate()} disabled={repriceMutation.isPending}>
            <RefreshCw className={cn('mr-2 h-4 w-4', repriceMutation.isPending && 'animate-spin')} />
            Refresh prices
          </Button>
          <Button variant="outline" onClick={exportTradeList} disabled={stats.trades === 0}>
            {canExport ? <Download className="mr-2 h-4 w-4" /> : <Lock className="mr-2 h-4 w-4" />}
            Export trade list
          </Button>
          <Button onClick={() => setShowConfirmDialog(true)} disabled={inBalance} className="bg-blue-600 hover:bg-blue-700">
            Rebalance index
          </Button>
        </div>
      </div>

      {!data.initialised && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>
            This index hasn't been calculated yet, so there are no holdings to measure drift against. Use
            "Refresh prices" to price it first.
          </p>
        </div>
      )}

      {unpriced.length > 0 && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>
            No price is available for {unpriced.map((c) => c.ticker).join(', ')}. A rebalance cannot value
            {unpriced.length === 1 ? ' it' : ' them'} and will leave {unpriced.length === 1 ? 'it' : 'them'} at zero weight.
          </p>
        </div>
      )}

      {/* Summary */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border bg-card p-5">
          <p className="text-sm text-muted-foreground">Largest drift</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{formatPercent(data.max_drift)}</p>
          <p className="mt-1 text-xs text-muted-foreground">Furthest any one name is from target</p>
        </div>
        <div className="rounded-xl border bg-card p-5">
          <p className="text-sm text-muted-foreground">Turnover to rebalance</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{formatPercent(data.turnover)}</p>
          <p className="mt-1 text-xs text-muted-foreground">One-way, full rebalance</p>
        </div>
        <div className="rounded-xl border bg-card p-5">
          <p className="text-sm text-muted-foreground">Trades above threshold</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{stats.trades}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {stats.buys} buy, {stats.sells} sell
          </p>
        </div>
        <div className="rounded-xl border bg-card p-5">
          <p className="text-sm text-muted-foreground">Last rebalanced</p>
          <p className="mt-1 text-2xl font-semibold">{data.last_rebalance ? formatDate(data.last_rebalance) : 'Never'}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Scheduled {(FREQUENCY_LABELS[data.rebalance_frequency] ?? data.rebalance_frequency).toLowerCase()}
            {data.last_calculated ? ` · priced ${formatDate(data.last_calculated)}` : ''}
          </p>
        </div>
      </div>

      {inBalance && data.initialised && (
        <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <CheckCircle className="h-4 w-4 flex-shrink-0" />
          Every constituent is at its target weight. Nothing to rebalance.
        </div>
      )}

      {/* Trade sizing */}
      <div className="rounded-xl border bg-card p-6">
        <h2 className="mb-1 text-lg font-semibold">Trade sizing</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Sizes the trade list for a portfolio tracking this index. These settings don't change the index itself.
        </p>
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <label htmlFor="portfolio-value" className="mb-2 block text-sm font-medium">Portfolio value</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
              <input
                id="portfolio-value"
                type="number"
                min={0}
                value={portfolioValue}
                onChange={(e) => setPortfolioValue(Math.max(0, Number(e.target.value)))}
                className="w-full rounded-lg border bg-background py-2 pl-7 pr-3 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <div>
            <label htmlFor="drift-threshold" className="mb-2 block text-sm font-medium">Minimum drift to trade</label>
            <select
              id="drift-threshold"
              value={driftThreshold}
              onChange={(e) => setDriftThreshold(Number(e.target.value))}
              className="w-full rounded-lg border bg-background px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value={0}>Any drift</option>
              <option value={0.0025}>0.25%</option>
              <option value={0.005}>0.5%</option>
              <option value={0.01}>1%</option>
              <option value={0.02}>2%</option>
              <option value={0.05}>5%</option>
            </select>
            <p className="mt-1 text-xs text-muted-foreground">Names inside this band are left alone in the trade list.</p>
          </div>
        </div>
      </div>

      {/* Drift table */}
      <div className="overflow-hidden rounded-xl border bg-card">
        <div className="border-b p-6">
          <h2 className="text-lg font-semibold">Current vs target weights</h2>
          <p className="text-sm text-muted-foreground">Sorted by drift. The marker shows the target; the bar shows the current weight.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px]">
            <thead className="bg-muted/50 text-sm text-muted-foreground">
              <tr>
                <th className="px-6 py-3 text-left font-medium">Constituent</th>
                <th className="px-6 py-3 text-left font-medium">Weight</th>
                <th className="px-6 py-3 text-right font-medium">Current</th>
                <th className="px-6 py-3 text-right font-medium">Target</th>
                <th className="px-6 py-3 text-right font-medium">Drift</th>
                <th className="px-6 py-3 text-center font-medium">Action</th>
                <th className="px-6 py-3 text-right font-medium">Trade value</th>
                <th className="px-6 py-3 text-right font-medium">Shares</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((row) => (
                <tr key={row.ticker} className={cn('hover:bg-muted/50', row.action === 'HOLD' && 'text-muted-foreground')}>
                  <td className="px-6 py-3">
                    <p className="font-mono font-medium text-foreground">{row.ticker}</p>
                    <p className="max-w-[14rem] truncate text-xs text-muted-foreground">{row.name}</p>
                  </td>
                  <td className="px-6 py-3">
                    <div className="relative h-2 w-32 rounded-full bg-muted">
                      <div
                        className="absolute inset-y-0 left-0 rounded-full bg-blue-600"
                        style={{ width: `${(row.currentWeight / maxWeight) * 100}%` }}
                      />
                      <div
                        className="absolute -top-1 h-4 w-0.5 bg-foreground"
                        style={{ left: `${(row.targetWeight / maxWeight) * 100}%` }}
                        title={`Target ${formatPercent(row.targetWeight)}`}
                      />
                    </div>
                  </td>
                  <td className="px-6 py-3 text-right tabular-nums">{formatPercent(row.currentWeight)}</td>
                  <td className="px-6 py-3 text-right tabular-nums">{formatPercent(row.targetWeight)}</td>
                  <td className="px-6 py-3 text-right font-medium tabular-nums">
                    {formatDrift(row.drift)}
                  </td>
                  <td className="px-6 py-3 text-center">
                    <span
                      className={cn(
                        'inline-flex rounded px-2 py-1 text-xs font-medium',
                        row.action === 'BUY' && 'bg-emerald-100 text-emerald-800',
                        row.action === 'SELL' && 'bg-rose-100 text-rose-800',
                        row.action === 'HOLD' && 'bg-muted text-muted-foreground'
                      )}
                    >
                      {row.action === 'BUY' ? 'Buy' : row.action === 'SELL' ? 'Sell' : 'Hold'}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-right tabular-nums">
                    {row.action !== 'HOLD' ? formatCurrency(row.tradeValue) : '–'}
                  </td>
                  <td className="px-6 py-3 text-right font-mono tabular-nums">
                    {row.action !== 'HOLD' && row.shares !== null
                      ? row.shares.toLocaleString('en-US', { maximumFractionDigits: 2 })
                      : '–'}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-6 py-10 text-center text-muted-foreground">
                    This index has no constituents yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirm */}
      {showConfirmDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setShowConfirmDialog(false)}>
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="rebalance-title"
            className="w-full max-w-md rounded-xl bg-background p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="rebalance-title" className="text-xl font-semibold">Rebalance {index.name}?</h2>
            <p className="mt-2 text-muted-foreground">
              Prices are refreshed, then every constituent is reset to its target weight. Turnover is about{' '}
              <strong className="text-foreground">{formatPercent(data.turnover)}</strong>.
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              The index level does not change: a rebalance reallocates holdings and records a rebalance date. It
              can't be undone.
            </p>
            <div className="mt-6 flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setShowConfirmDialog(false)}>
                Cancel
              </Button>
              <Button
                className="flex-1 bg-blue-600 hover:bg-blue-700"
                onClick={() => rebalanceMutation.mutate()}
                disabled={rebalanceMutation.isPending}
              >
                {rebalanceMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Rebalance
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
