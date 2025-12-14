import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  ArrowLeft, 
  RefreshCw, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle,
  CheckCircle,
  Clock,
  Download,
  Calendar,
  ArrowUpDown,
  Target,
  Scale
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { indicesApi } from '@/lib/api'
import { formatPercent, formatCurrency } from '@/lib/utils'

interface RebalancePreview {
  ticker: string
  name: string
  currentWeight: number
  targetWeight: number
  drift: number
  action: 'BUY' | 'SELL' | 'HOLD'
  tradeValue: number
  shares: number
}

export function RebalancingPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [rebalanceMethod, setRebalanceMethod] = useState<'full' | 'threshold'>('full')
  const [driftThreshold, setDriftThreshold] = useState(0.02) // 2% default
  const [portfolioValue, setPortfolioValue] = useState(1000000) // $1M default

  const { data: index, isLoading } = useQuery({
    queryKey: ['index', id],
    queryFn: () => indicesApi.get(id!),
    enabled: !!id,
  })

  const rebalanceMutation = useMutation({
    mutationFn: () => indicesApi.rebalance(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
      setShowConfirmDialog(false)
    },
  })

  // Calculate rebalance preview data
  const rebalanceData = useMemo<RebalancePreview[]>(() => {
    if (!index?.components) return []

    // Simulate current vs target weights (in real app, this comes from live prices)
    return index.components.map((component: any) => {
      const targetWeight = component.weight
      // Simulate drift (in production, this would come from actual market data)
      const driftPercent = (Math.random() - 0.5) * 0.1 // ±5% drift simulation
      const currentWeight = targetWeight * (1 + driftPercent)
      const drift = currentWeight - targetWeight
      
      let action: 'BUY' | 'SELL' | 'HOLD' = 'HOLD'
      if (drift > driftThreshold) action = 'SELL'
      else if (drift < -driftThreshold) action = 'BUY'

      const tradeValue = Math.abs(drift) * portfolioValue
      const sharePrice = component.market_cap ? component.market_cap / 1e9 * 10 : 100 // rough estimate
      const shares = Math.round(tradeValue / sharePrice)

      return {
        ticker: component.ticker,
        name: component.name || component.ticker,
        currentWeight,
        targetWeight,
        drift,
        action,
        tradeValue,
        shares
      }
    }).sort((a, b) => Math.abs(b.drift) - Math.abs(a.drift))
  }, [index, driftThreshold, portfolioValue])

  const stats = useMemo(() => {
    const totalDrift = rebalanceData.reduce((sum, item) => sum + Math.abs(item.drift), 0)
    const tradesNeeded = rebalanceData.filter(item => item.action !== 'HOLD').length
    const buyCount = rebalanceData.filter(item => item.action === 'BUY').length
    const sellCount = rebalanceData.filter(item => item.action === 'SELL').length
    const totalTradeValue = rebalanceData.reduce((sum, item) => 
      item.action !== 'HOLD' ? sum + item.tradeValue : sum, 0)
    const turnover = totalTradeValue / portfolioValue

    return { totalDrift, tradesNeeded, buyCount, sellCount, totalTradeValue, turnover }
  }, [rebalanceData, portfolioValue])

  const exportTradeList = () => {
    const trades = rebalanceData.filter(item => item.action !== 'HOLD')
    const csv = [
      'Ticker,Name,Action,Current Weight,Target Weight,Drift,Trade Value,Shares',
      ...trades.map(t => 
        `${t.ticker},"${t.name}",${t.action},${(t.currentWeight * 100).toFixed(2)}%,${(t.targetWeight * 100).toFixed(2)}%,${(t.drift * 100).toFixed(2)}%,$${t.tradeValue.toFixed(2)},${t.shares}`
      )
    ].join('\n')
    
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${index?.identifier || 'index'}_rebalance_trades.csv`
    a.click()
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  if (!index) {
    return <div className="text-center py-12">Index not found</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to={`/indices/${id}`} className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to {index.name}
          </Link>
          <h1 className="text-3xl font-bold">Rebalancing</h1>
          <p className="text-muted-foreground">Review and execute portfolio rebalancing</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportTradeList}>
            <Download className="h-4 w-4 mr-2" />
            Export Trade List
          </Button>
          <Button 
            onClick={() => setShowConfirmDialog(true)}
            disabled={stats.tradesNeeded === 0}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Execute Rebalance
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid md:grid-cols-5 gap-4">
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl p-4 text-white">
          <div className="flex items-center gap-2 mb-2">
            <Scale className="h-5 w-5 text-blue-400" />
            <p className="text-sm text-slate-300">Total Drift</p>
          </div>
          <p className="text-2xl font-bold">{formatPercent(stats.totalDrift)}</p>
        </div>
        <div className="bg-gradient-to-br from-emerald-900 to-emerald-800 rounded-xl p-4 text-white">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-5 w-5 text-emerald-400" />
            <p className="text-sm text-emerald-200">Buy Orders</p>
          </div>
          <p className="text-2xl font-bold">{stats.buyCount}</p>
        </div>
        <div className="bg-gradient-to-br from-rose-900 to-rose-800 rounded-xl p-4 text-white">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="h-5 w-5 text-rose-400" />
            <p className="text-sm text-rose-200">Sell Orders</p>
          </div>
          <p className="text-2xl font-bold">{stats.sellCount}</p>
        </div>
        <div className="bg-gradient-to-br from-amber-900 to-amber-800 rounded-xl p-4 text-white">
          <div className="flex items-center gap-2 mb-2">
            <ArrowUpDown className="h-5 w-5 text-amber-400" />
            <p className="text-sm text-amber-200">Turnover</p>
          </div>
          <p className="text-2xl font-bold">{formatPercent(stats.turnover)}</p>
        </div>
        <div className="bg-gradient-to-br from-violet-900 to-violet-800 rounded-xl p-4 text-white">
          <div className="flex items-center gap-2 mb-2">
            <Target className="h-5 w-5 text-violet-400" />
            <p className="text-sm text-violet-200">Trade Value</p>
          </div>
          <p className="text-2xl font-bold">{formatCurrency(stats.totalTradeValue)}</p>
        </div>
      </div>

      {/* Settings */}
      <div className="bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Rebalancing Settings</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium mb-2">Portfolio Value</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
              <input
                type="number"
                value={portfolioValue}
                onChange={(e) => setPortfolioValue(Number(e.target.value))}
                className="w-full pl-7 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Drift Threshold</label>
            <select
              value={driftThreshold}
              onChange={(e) => setDriftThreshold(Number(e.target.value))}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value={0.005}>0.5%</option>
              <option value={0.01}>1%</option>
              <option value={0.02}>2%</option>
              <option value={0.03}>3%</option>
              <option value={0.05}>5%</option>
            </select>
            <p className="text-xs text-muted-foreground mt-1">Minimum drift to trigger trade</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Rebalance Method</label>
            <select
              value={rebalanceMethod}
              onChange={(e) => setRebalanceMethod(e.target.value as 'full' | 'threshold')}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="full">Full Rebalance</option>
              <option value="threshold">Threshold Only</option>
            </select>
            <p className="text-xs text-muted-foreground mt-1">Full or only drifted positions</p>
          </div>
        </div>
      </div>

      {/* Weight Comparison Chart */}
      <div className="bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Weight Comparison</h2>
        <div className="space-y-3">
          {rebalanceData.slice(0, 10).map((item) => (
            <div key={item.ticker} className="flex items-center gap-4">
              <div className="w-16 font-mono font-medium">{item.ticker}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex-1 h-6 bg-slate-100 rounded-full overflow-hidden relative">
                    {/* Target weight bar */}
                    <div 
                      className="absolute inset-y-0 left-0 bg-slate-300 rounded-full"
                      style={{ width: `${Math.min(item.targetWeight * 100 * 5, 100)}%` }}
                    />
                    {/* Current weight bar */}
                    <div 
                      className={`absolute inset-y-0 left-0 rounded-full ${
                        item.action === 'BUY' ? 'bg-emerald-500' : 
                        item.action === 'SELL' ? 'bg-rose-500' : 'bg-blue-500'
                      }`}
                      style={{ width: `${Math.min(item.currentWeight * 100 * 5, 100)}%` }}
                    />
                  </div>
                  <div className="w-20 text-right text-sm">
                    <span className={item.drift > 0 ? 'text-rose-600' : item.drift < 0 ? 'text-emerald-600' : ''}>
                      {item.drift > 0 ? '+' : ''}{formatPercent(item.drift)}
                    </span>
                  </div>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Current: {formatPercent(item.currentWeight)}</span>
                  <span>Target: {formatPercent(item.targetWeight)}</span>
                </div>
              </div>
              <div className={`px-2 py-1 rounded text-xs font-medium ${
                item.action === 'BUY' ? 'bg-emerald-100 text-emerald-700' :
                item.action === 'SELL' ? 'bg-rose-100 text-rose-700' :
                'bg-slate-100 text-slate-600'
              }`}>
                {item.action}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Trade Preview Table */}
      <div className="bg-card rounded-xl border overflow-hidden">
        <div className="p-6 border-b">
          <h2 className="text-lg font-semibold">Trade Preview</h2>
          <p className="text-sm text-muted-foreground">Required trades to reach target weights</p>
        </div>
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Ticker</th>
              <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Name</th>
              <th className="text-center px-6 py-3 text-sm font-medium text-muted-foreground">Action</th>
              <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Current</th>
              <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Target</th>
              <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Drift</th>
              <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Trade Value</th>
              <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Est. Shares</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {rebalanceData.map((item) => (
              <tr key={item.ticker} className={`hover:bg-muted/50 ${item.action === 'HOLD' ? 'opacity-50' : ''}`}>
                <td className="px-6 py-4 font-mono font-medium">{item.ticker}</td>
                <td className="px-6 py-4 text-sm">{item.name}</td>
                <td className="px-6 py-4 text-center">
                  <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                    item.action === 'BUY' ? 'bg-emerald-100 text-emerald-700' :
                    item.action === 'SELL' ? 'bg-rose-100 text-rose-700' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {item.action === 'BUY' && <TrendingUp className="h-3 w-3 mr-1" />}
                    {item.action === 'SELL' && <TrendingDown className="h-3 w-3 mr-1" />}
                    {item.action}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">{formatPercent(item.currentWeight)}</td>
                <td className="px-6 py-4 text-right">{formatPercent(item.targetWeight)}</td>
                <td className={`px-6 py-4 text-right font-medium ${
                  item.drift > 0 ? 'text-rose-600' : item.drift < 0 ? 'text-emerald-600' : ''
                }`}>
                  {item.drift > 0 ? '+' : ''}{formatPercent(item.drift)}
                </td>
                <td className="px-6 py-4 text-right">{item.action !== 'HOLD' ? formatCurrency(item.tradeValue) : '-'}</td>
                <td className="px-6 py-4 text-right font-mono">{item.action !== 'HOLD' ? item.shares.toLocaleString() : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Rebalancing Schedule */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Rebalancing Schedule</h2>
          <Button variant="outline" size="sm">
            <Calendar className="h-4 w-4 mr-2" />
            Edit Schedule
          </Button>
        </div>
        <div className="grid md:grid-cols-4 gap-4">
          <div className="bg-muted/50 rounded-lg p-4">
            <p className="text-sm text-muted-foreground mb-1">Frequency</p>
            <p className="font-medium capitalize">{index.rebalancing_frequency || 'Quarterly'}</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <p className="text-sm text-muted-foreground mb-1">Last Rebalance</p>
            <p className="font-medium">Dec 1, 2024</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <p className="text-sm text-muted-foreground mb-1">Next Scheduled</p>
            <p className="font-medium">Mar 1, 2025</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <p className="text-sm text-muted-foreground mb-1">Days Until</p>
            <p className="font-medium">77 days</p>
          </div>
        </div>
      </div>

      {/* Confirm Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-full bg-amber-100">
                <AlertTriangle className="h-6 w-6 text-amber-600" />
              </div>
              <h2 className="text-xl font-semibold">Confirm Rebalance</h2>
            </div>
            <p className="text-muted-foreground mb-4">
              You are about to execute {stats.tradesNeeded} trades with a total value of{' '}
              <strong>{formatCurrency(stats.totalTradeValue)}</strong>. This action will update 
              all component weights to their target values.
            </p>
            <div className="bg-slate-50 rounded-lg p-4 mb-4">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>Buy Orders: <span className="font-medium text-emerald-600">{stats.buyCount}</span></div>
                <div>Sell Orders: <span className="font-medium text-rose-600">{stats.sellCount}</span></div>
                <div>Turnover: <span className="font-medium">{formatPercent(stats.turnover)}</span></div>
                <div>Est. Cost: <span className="font-medium">{formatCurrency(stats.totalTradeValue * 0.001)}</span></div>
              </div>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowConfirmDialog(false)}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600"
                onClick={() => rebalanceMutation.mutate()}
                disabled={rebalanceMutation.isPending}
              >
                {rebalanceMutation.isPending ? 'Executing...' : 'Confirm Rebalance'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

