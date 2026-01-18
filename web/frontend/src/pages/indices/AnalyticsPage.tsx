import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  ArrowLeft, 
  TrendingUp, 
  TrendingDown, 
  BarChart3,
  PieChart,
  Activity,
  AlertTriangle,
  Calendar,
  Download,
  Maximize2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { indicesApi } from '@/lib/api'
import { formatPercent, formatCurrency } from '@/lib/utils'

// Simple line chart component (in production, use Recharts or similar)
function MiniChart({ data, color = '#3B82F6', height = 60 }: { data: number[], color?: string, height?: number }) {
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  
  const points = data.map((value, i) => {
    const x = (i / (data.length - 1)) * 100
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  }).join(' ')

  return (
    <svg viewBox={`0 0 100 ${height}`} className="w-full" style={{ height }}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// Donut chart for sector allocation
function DonutChart({ data }: { data: { name: string, value: number, color: string }[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0)
  let currentAngle = -90
  
  return (
    <svg viewBox="0 0 100 100" className="w-full max-w-[200px] mx-auto">
      {data.map((segment, i) => {
        const angle = (segment.value / total) * 360
        const startAngle = currentAngle
        const endAngle = currentAngle + angle
        currentAngle = endAngle
        
        const startRad = (startAngle * Math.PI) / 180
        const endRad = (endAngle * Math.PI) / 180
        
        const x1 = 50 + 40 * Math.cos(startRad)
        const y1 = 50 + 40 * Math.sin(startRad)
        const x2 = 50 + 40 * Math.cos(endRad)
        const y2 = 50 + 40 * Math.sin(endRad)
        
        const largeArc = angle > 180 ? 1 : 0
        
        return (
          <path
            key={i}
            d={`M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`}
            fill={segment.color}
            stroke="white"
            strokeWidth="1"
          />
        )
      })}
      <circle cx="50" cy="50" r="25" fill="white" />
    </svg>
  )
}

export function AnalyticsPage() {
  const { id } = useParams<{ id: string }>()
  const [timeRange, setTimeRange] = useState<'1M' | '3M' | '6M' | '1Y' | 'YTD' | 'ALL'>('1Y')

  const { data: index, isLoading } = useQuery({
    queryKey: ['index', id],
    queryFn: () => indicesApi.get(id!),
    enabled: !!id,
  })

  // Generate simulated performance data
  const performanceData = useMemo(() => {
    const days = timeRange === '1M' ? 30 : timeRange === '3M' ? 90 : timeRange === '6M' ? 180 : 365
    const data = []
    let value = 1000
    for (let i = 0; i < days; i++) {
      value = value * (1 + (Math.random() - 0.48) * 0.02)
      data.push(value)
    }
    return data
  }, [timeRange])

  const benchmarkData = useMemo(() => {
    const days = performanceData.length
    const data = []
    let value = 1000
    for (let i = 0; i < days; i++) {
      value = value * (1 + (Math.random() - 0.47) * 0.015)
      data.push(value)
    }
    return data
  }, [performanceData.length])

  // Calculate metrics
  const metrics = useMemo(() => {
    const startValue = performanceData[0]
    const endValue = performanceData[performanceData.length - 1]
    const totalReturn = (endValue - startValue) / startValue
    
    // Calculate daily returns
    const dailyReturns = performanceData.slice(1).map((val, i) => 
      (val - performanceData[i]) / performanceData[i]
    )
    
    // Volatility (annualized)
    const avgReturn = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length
    const variance = dailyReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / dailyReturns.length
    const volatility = Math.sqrt(variance) * Math.sqrt(252)
    
    // Max Drawdown
    let peak = performanceData[0]
    let maxDrawdown = 0
    for (const val of performanceData) {
      if (val > peak) peak = val
      const drawdown = (peak - val) / peak
      if (drawdown > maxDrawdown) maxDrawdown = drawdown
    }
    
    // Sharpe Ratio (assuming 4% risk-free rate)
    const annualizedReturn = totalReturn * (252 / performanceData.length)
    const sharpeRatio = (annualizedReturn - 0.04) / volatility
    
    // Benchmark comparison
    const benchmarkReturn = (benchmarkData[benchmarkData.length - 1] - benchmarkData[0]) / benchmarkData[0]
    const alpha = totalReturn - benchmarkReturn

    return {
      totalReturn,
      annualizedReturn,
      volatility,
      maxDrawdown,
      sharpeRatio,
      benchmarkReturn,
      alpha,
      currentValue: endValue
    }
  }, [performanceData, benchmarkData])

  // Sector allocation data
  const sectorAllocation = useMemo(() => {
    if (!index?.components) return []
    const sectors: Record<string, number> = {}
    index.components.forEach((c: any) => {
      const sector = c.sector || 'Other'
      sectors[sector] = (sectors[sector] || 0) + (c.weight || 0)
    })
    
    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']
    return Object.entries(sectors).map(([name, value], i) => ({
      name,
      value,
      color: colors[i % colors.length]
    }))
  }, [index])

  // Risk metrics
  const riskMetrics = useMemo(() => ({
    var95: metrics.volatility * 1.645 * Math.sqrt(1/252), // 1-day 95% VaR
    var99: metrics.volatility * 2.326 * Math.sqrt(1/252), // 1-day 99% VaR
    beta: 0.95 + Math.random() * 0.2, // Simulated
    trackingError: 0.02 + Math.random() * 0.03, // Simulated
    informationRatio: metrics.alpha / 0.03, // Simulated tracking error
  }), [metrics])

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
          <h1 className="text-3xl font-bold">Performance Analytics</h1>
          <p className="text-muted-foreground">Detailed performance metrics and risk analysis</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
          <Button variant="outline">
            <Maximize2 className="h-4 w-4 mr-2" />
            Full Screen
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-5 text-white">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-5 w-5 text-blue-200" />
            <p className="text-sm text-blue-100">Total Return</p>
          </div>
          <p className={`text-3xl font-bold ${metrics.totalReturn >= 0 ? '' : 'text-red-200'}`}>
            {metrics.totalReturn >= 0 ? '+' : ''}{formatPercent(metrics.totalReturn)}
          </p>
          <p className="text-sm text-blue-200 mt-1">vs Benchmark: {formatPercent(metrics.alpha)}</p>
        </div>
        <div className="bg-gradient-to-br from-emerald-600 to-emerald-700 rounded-xl p-5 text-white">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-5 w-5 text-emerald-200" />
            <p className="text-sm text-emerald-100">Sharpe Ratio</p>
          </div>
          <p className="text-3xl font-bold">{metrics.sharpeRatio.toFixed(2)}</p>
          <p className="text-sm text-emerald-200 mt-1">Risk-adjusted return</p>
        </div>
        <div className="bg-gradient-to-br from-amber-600 to-amber-700 rounded-xl p-5 text-white">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="h-5 w-5 text-amber-200" />
            <p className="text-sm text-amber-100">Volatility</p>
          </div>
          <p className="text-3xl font-bold">{formatPercent(metrics.volatility)}</p>
          <p className="text-sm text-amber-200 mt-1">Annualized</p>
        </div>
        <div className="bg-gradient-to-br from-rose-600 to-rose-700 rounded-xl p-5 text-white">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="h-5 w-5 text-rose-200" />
            <p className="text-sm text-rose-100">Max Drawdown</p>
          </div>
          <p className="text-3xl font-bold">-{formatPercent(metrics.maxDrawdown)}</p>
          <p className="text-sm text-rose-200 mt-1">Peak to trough</p>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">Performance vs Benchmark</h2>
          <div className="flex gap-1 bg-muted rounded-lg p-1">
            {(['1M', '3M', '6M', '1Y', 'YTD', 'ALL'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  timeRange === range 
                    ? 'bg-white shadow text-foreground' 
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>
        <div className="h-64 relative">
          <div className="absolute inset-0">
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
              {/* Grid lines */}
              {[0, 25, 50, 75, 100].map((y) => (
                <line key={y} x1="0" y1={y} x2="100" y2={y} stroke="#E5E7EB" strokeWidth="0.2" />
              ))}
              
              {/* Benchmark line */}
              <polyline
                points={benchmarkData.map((val, i) => {
                  const min = Math.min(...performanceData, ...benchmarkData)
                  const max = Math.max(...performanceData, ...benchmarkData)
                  const x = (i / (benchmarkData.length - 1)) * 100
                  const y = 100 - ((val - min) / (max - min)) * 100
                  return `${x},${y}`
                }).join(' ')}
                fill="none"
                stroke="#94A3B8"
                strokeWidth="0.5"
                strokeDasharray="2,2"
              />
              
              {/* Index line */}
              <polyline
                points={performanceData.map((val, i) => {
                  const min = Math.min(...performanceData, ...benchmarkData)
                  const max = Math.max(...performanceData, ...benchmarkData)
                  const x = (i / (performanceData.length - 1)) * 100
                  const y = 100 - ((val - min) / (max - min)) * 100
                  return `${x},${y}`
                }).join(' ')}
                fill="none"
                stroke="#3B82F6"
                strokeWidth="0.8"
              />
            </svg>
          </div>
        </div>
        <div className="flex items-center justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-blue-500" />
            <span className="text-sm">{index.name}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-slate-400 border-dashed" />
            <span className="text-sm text-muted-foreground">S&P 500 Benchmark</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Sector Allocation */}
        <div className="bg-card rounded-xl border p-6">
          <div className="flex items-center gap-2 mb-4">
            <PieChart className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-lg font-semibold">Sector Allocation</h2>
          </div>
          <div className="flex items-center gap-6">
            <DonutChart data={sectorAllocation} />
            <div className="flex-1 space-y-2">
              {sectorAllocation.slice(0, 6).map((sector) => (
                <div key={sector.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: sector.color }} />
                    <span className="text-sm">{sector.name}</span>
                  </div>
                  <span className="text-sm font-medium">{formatPercent(sector.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Risk Metrics */}
        <div className="bg-card rounded-xl border p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-lg font-semibold">Risk Metrics</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-muted/50 rounded-lg p-4">
              <p className="text-sm text-muted-foreground">VaR (95%)</p>
              <p className="text-xl font-bold text-rose-600">-{formatPercent(riskMetrics.var95)}</p>
              <p className="text-xs text-muted-foreground">1-day</p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <p className="text-sm text-muted-foreground">VaR (99%)</p>
              <p className="text-xl font-bold text-rose-600">-{formatPercent(riskMetrics.var99)}</p>
              <p className="text-xs text-muted-foreground">1-day</p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <p className="text-sm text-muted-foreground">Beta</p>
              <p className="text-xl font-bold">{riskMetrics.beta.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground">vs S&P 500</p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <p className="text-sm text-muted-foreground">Tracking Error</p>
              <p className="text-xl font-bold">{formatPercent(riskMetrics.trackingError)}</p>
              <p className="text-xs text-muted-foreground">Annualized</p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4 col-span-2">
              <p className="text-sm text-muted-foreground">Information Ratio</p>
              <p className="text-xl font-bold">{riskMetrics.informationRatio.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground">Alpha / Tracking Error</p>
            </div>
          </div>
        </div>
      </div>

      {/* Monthly Returns Heatmap */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Monthly Returns</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left py-2 px-3 font-medium text-muted-foreground">Year</th>
                {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'YTD'].map(m => (
                  <th key={m} className="text-center py-2 px-2 font-medium text-muted-foreground">{m}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[2024, 2023].map(year => (
                <tr key={year} className="border-t">
                  <td className="py-2 px-3 font-medium">{year}</td>
                  {Array(13).fill(0).map((_, i) => {
                    const ret = (Math.random() - 0.45) * 0.1
                    const intensity = Math.min(Math.abs(ret) * 10, 1)
                    const bgColor = ret >= 0 
                      ? `rgba(16, 185, 129, ${intensity})` 
                      : `rgba(239, 68, 68, ${intensity})`
                    return (
                      <td key={i} className="text-center py-2 px-2">
                        <div 
                          className="rounded px-2 py-1 text-xs font-medium"
                          style={{ backgroundColor: bgColor }}
                        >
                          {ret >= 0 ? '+' : ''}{(ret * 100).toFixed(1)}%
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detailed Statistics */}
      <div className="bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Detailed Statistics</h2>
        <div className="grid md:grid-cols-4 gap-6">
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Returns</h3>
            <div className="space-y-2">
              <div className="flex justify-between"><span>1 Month</span><span className="font-medium">+2.4%</span></div>
              <div className="flex justify-between"><span>3 Month</span><span className="font-medium">+5.8%</span></div>
              <div className="flex justify-between"><span>6 Month</span><span className="font-medium">+8.2%</span></div>
              <div className="flex justify-between"><span>1 Year</span><span className="font-medium">{formatPercent(metrics.totalReturn)}</span></div>
              <div className="flex justify-between"><span>Since Inception</span><span className="font-medium">+45.2%</span></div>
            </div>
          </div>
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Volatility</h3>
            <div className="space-y-2">
              <div className="flex justify-between"><span>Daily</span><span className="font-medium">{formatPercent(metrics.volatility / Math.sqrt(252))}</span></div>
              <div className="flex justify-between"><span>Monthly</span><span className="font-medium">{formatPercent(metrics.volatility / Math.sqrt(12))}</span></div>
              <div className="flex justify-between"><span>Annualized</span><span className="font-medium">{formatPercent(metrics.volatility)}</span></div>
              <div className="flex justify-between"><span>Downside</span><span className="font-medium">{formatPercent(metrics.volatility * 0.8)}</span></div>
              <div className="flex justify-between"><span>Upside</span><span className="font-medium">{formatPercent(metrics.volatility * 1.1)}</span></div>
            </div>
          </div>
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Drawdowns</h3>
            <div className="space-y-2">
              <div className="flex justify-between"><span>Maximum</span><span className="font-medium text-rose-600">-{formatPercent(metrics.maxDrawdown)}</span></div>
              <div className="flex justify-between"><span>Average</span><span className="font-medium">-{formatPercent(metrics.maxDrawdown * 0.5)}</span></div>
              <div className="flex justify-between"><span>Current</span><span className="font-medium">-{formatPercent(metrics.maxDrawdown * 0.2)}</span></div>
              <div className="flex justify-between"><span>Recovery (avg)</span><span className="font-medium">42 days</span></div>
              <div className="flex justify-between"><span>Time Underwater</span><span className="font-medium">28%</span></div>
            </div>
          </div>
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Ratios</h3>
            <div className="space-y-2">
              <div className="flex justify-between"><span>Sharpe</span><span className="font-medium">{metrics.sharpeRatio.toFixed(2)}</span></div>
              <div className="flex justify-between"><span>Sortino</span><span className="font-medium">{(metrics.sharpeRatio * 1.3).toFixed(2)}</span></div>
              <div className="flex justify-between"><span>Calmar</span><span className="font-medium">{(metrics.annualizedReturn / metrics.maxDrawdown).toFixed(2)}</span></div>
              <div className="flex justify-between"><span>Information</span><span className="font-medium">{riskMetrics.informationRatio.toFixed(2)}</span></div>
              <div className="flex justify-between"><span>Treynor</span><span className="font-medium">{((metrics.annualizedReturn - 0.04) / riskMetrics.beta).toFixed(2)}</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}



