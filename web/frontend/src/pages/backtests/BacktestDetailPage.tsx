import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, AlertTriangle } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { backtestsApi } from '@/lib/api'
import { formatPercent, formatCurrency, formatDate } from '@/lib/utils'

export function BacktestDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: backtest, isLoading } = useQuery({
    queryKey: ['backtest', id],
    queryFn: () => backtestsApi.get(id!),
    enabled: !!id,
    // Auto-refetch every 2 seconds while backtest is running
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'pending' || status === 'running' ? 2000 : false
    },
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  if (!backtest) {
    return <div className="text-center py-12">Backtest not found</div>
  }

  // Prepare chart data
  const chartData = backtest.daily_values
    ? Object.entries(backtest.daily_values).map(([date, value]) => ({
        date,
        portfolio: value as number,
        benchmark: backtest.benchmark_values?.[date] as number | undefined,
      }))
    : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/backtests" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Backtests
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold">{backtest.name}</h1>
          {backtest.status === 'pending' && (
            <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-full">Pending</span>
          )}
          {backtest.status === 'running' && (
            <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full flex items-center gap-1">
              <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Running ({Math.round(backtest.progress * 100)}%)
            </span>
          )}
          {backtest.status === 'completed' && (
            <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">Completed</span>
          )}
          {backtest.status === 'failed' && (
            <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded-full">Failed</span>
          )}
        </div>
        <p className="text-muted-foreground">
          {formatDate(backtest.start_date)} - {formatDate(backtest.end_date)}
        </p>
      </div>

      {/* Error message if failed */}
      {backtest.status === 'failed' && backtest.error_message && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-medium">Backtest Failed</p>
          <p className="text-sm">{backtest.error_message}</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid md:grid-cols-4 gap-4">
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Total Return</p>
          <p className={`text-2xl font-bold ${(backtest.total_return || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {backtest.total_return !== null ? formatPercent(backtest.total_return) : '-'}
          </p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
          <p className="text-2xl font-bold">{backtest.sharpe_ratio?.toFixed(2) || '-'}</p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Max Drawdown</p>
          <p className="text-2xl font-bold text-red-500">
            {backtest.max_drawdown ? formatPercent(-backtest.max_drawdown) : '-'}
          </p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Volatility</p>
          <p className="text-2xl font-bold">{backtest.volatility ? formatPercent(backtest.volatility) : '-'}</p>
        </div>
      </div>

      {/* Methodology caveat. Sits directly under the headline numbers on purpose:
          these results are optimistic, and someone reading them to size an
          allocation needs to know that before they scroll past. */}
      {backtest.methodology_caveat && backtest.status === 'completed' && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-900 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 mt-0.5 text-amber-600 shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-amber-900 dark:text-amber-200">
                How to read these results
              </p>
              <p className="text-amber-800/80 dark:text-amber-300/80 mt-1">
                {backtest.methodology_caveat}
              </p>
              {backtest.transaction_cost_bps !== undefined && (
                <p className="text-amber-800/70 dark:text-amber-300/70 mt-1">
                  Turnover is charged at {backtest.transaction_cost_bps} bps per rebalance.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Performance</h2>
        <div className="h-80">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                  labelFormatter={(value) => formatDate(value)}
                  formatter={(value: number) => [formatCurrency(value), '']}
                />
                <Legend />
                <Line type="monotone" dataKey="portfolio" name="Portfolio" stroke="hsl(var(--primary))" dot={false} />
                {backtest.benchmark_values && (
                  <Line type="monotone" dataKey="benchmark" name="Benchmark" stroke="hsl(var(--muted-foreground))" dot={false} />
                )}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              No chart data available
            </div>
          )}
        </div>
      </div>

      {/* Details */}
      <div className="bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Details</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Initial Value</p>
            <p className="font-medium">{formatCurrency(backtest.initial_value)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Final Value</p>
            <p className="font-medium">{backtest.final_value ? formatCurrency(backtest.final_value) : '-'}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Benchmark</p>
            <p className="font-medium font-mono">{backtest.benchmark_ticker || 'None'}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Benchmark Return</p>
            <p className="font-medium">{backtest.benchmark_return !== null ? formatPercent(backtest.benchmark_return) : '-'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
