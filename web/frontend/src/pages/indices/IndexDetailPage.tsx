import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Edit, Trash2, Play, RefreshCw, X, BarChart3, Scale } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { indicesApi, backtestsApi, marketDataProvidersApi } from '@/lib/api'
import { formatCurrency, formatPercent, formatMarketCap } from '@/lib/utils'

export function IndexDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Backtest dialog state
  const [showBacktestDialog, setShowBacktestDialog] = useState(false)
  const [backtestName, setBacktestName] = useState('')
  const [backtestStartDate, setBacktestStartDate] = useState('')
  const [backtestEndDate, setBacktestEndDate] = useState('')
  const [backtestBenchmark, setBacktestBenchmark] = useState('SPY')

  // Add component dialog state
  const [showAddComponentDialog, setShowAddComponentDialog] = useState(false)
  const [newComponentTicker, setNewComponentTicker] = useState('')
  const [newComponentWeight, setNewComponentWeight] = useState('0.1')

  const { data: index, isLoading } = useQuery({
    queryKey: ['index', id],
    queryFn: () => indicesApi.get(id!),
    enabled: !!id,
  })

  // Fetch active data source
  const { data: activeDataSource } = useQuery({
    queryKey: ['activeDataSource'],
    queryFn: marketDataProvidersApi.getActive,
  })

  const deleteMutation = useMutation({
    mutationFn: () => indicesApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['indices'] })
      navigate('/indices')
    },
  })

  const calculateMutation = useMutation({
    mutationFn: () => indicesApi.calculate(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
    },
  })

  const backtestMutation = useMutation({
    mutationFn: (data: { name: string; start_date: string; end_date: string; benchmark_ticker?: string }) =>
      backtestsApi.create(id!, data),
    onSuccess: (backtest) => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
      setShowBacktestDialog(false)
      navigate(`/backtests/${backtest.id}`)
    },
  })

  const addComponentMutation = useMutation({
    mutationFn: (data: { ticker: string; weight: number }) =>
      indicesApi.addComponent(id!, data.ticker, data.weight),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
      setShowAddComponentDialog(false)
      setNewComponentTicker('')
      setNewComponentWeight('0.1')
    },
  })

  const updateStatusMutation = useMutation({
    mutationFn: (newStatus: string) =>
      indicesApi.update(id!, { status: newStatus }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index', id] })
      queryClient.invalidateQueries({ queryKey: ['indices'] })
    },
  })

  const handleRunBacktest = () => {
    // Set default dates (1 year ago to today)
    const today = new Date()
    const oneYearAgo = new Date()
    oneYearAgo.setFullYear(today.getFullYear() - 1)

    setBacktestName(`${index?.name || 'Index'} Backtest`)
    setBacktestStartDate(oneYearAgo.toISOString().split('T')[0])
    setBacktestEndDate(today.toISOString().split('T')[0])
    setShowBacktestDialog(true)
  }

  const submitBacktest = () => {

    backtestMutation.mutate({
      name: backtestName,
      start_date: backtestStartDate,
      end_date: backtestEndDate,
      benchmark_ticker: backtestBenchmark || undefined,
    })
  }

  const submitAddComponent = () => {

    addComponentMutation.mutate({
      ticker: newComponentTicker.toUpperCase(),
      weight: parseFloat(newComponentWeight),
    })
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
          <Link to="/indices" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Indices
          </Link>
          <h1 className="text-3xl font-bold">{index.name}</h1>
          <p className="text-muted-foreground font-mono">{index.identifier}</p>
        </div>
        <div className="flex gap-2">
          <Link to={`/indices/${id}/analytics`}>
            <Button variant="outline" className="bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-200 hover:from-emerald-100 hover:to-teal-100">
              <BarChart3 className="h-4 w-4 mr-2 text-emerald-600" />
              Analytics
            </Button>
          </Link>
          <Link to={`/indices/${id}/rebalancing`}>
            <Button variant="outline" className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 hover:from-blue-100 hover:to-indigo-100">
              <Scale className="h-4 w-4 mr-2 text-blue-600" />
              Rebalancing
            </Button>
          </Link>
          <Button variant="outline" onClick={() => calculateMutation.mutate()} disabled={calculateMutation.isPending}>
            <RefreshCw className={`h-4 w-4 mr-2 ${calculateMutation.isPending ? 'animate-spin' : ''}`} />
            Calculate
          </Button>
          <Link to={`/indices/${id}/edit`}>
            <Button variant="outline">
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
          </Link>
          <Button variant="destructive" onClick={() => deleteMutation.mutate()}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-4 gap-4">
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Current Value</p>
          <p className="text-2xl font-bold">
            {index.current_value ? formatCurrency(index.current_value) : '-'}
          </p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Components</p>
          <p className="text-2xl font-bold">{index.component_count}</p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">Weighting</p>
          <p className="text-lg font-medium capitalize">{index.weighting_method.replace('_', ' ')}</p>
        </div>
        <div className="bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground mb-2">Status</p>
          <select
            value={index.status}
            onChange={(e) => updateStatusMutation.mutate(e.target.value)}
            disabled={updateStatusMutation.isPending}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg border-2 focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer ${index.status === 'active'
              ? 'bg-green-50 border-green-200 text-green-700'
              : index.status === 'draft'
                ? 'bg-yellow-50 border-yellow-200 text-yellow-700'
                : index.status === 'paused'
                  ? 'bg-gray-50 border-gray-200 text-gray-700'
                  : 'bg-gray-50 border-gray-200 text-gray-700'
              } ${updateStatusMutation.isPending ? 'opacity-50' : ''}`}
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      {/* Description */}
      {index.description && (
        <div className="bg-card rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-2">Description</h2>
          <p className="text-muted-foreground">{index.description}</p>
        </div>
      )}

      {/* Components */}
      <div className="bg-card rounded-xl border overflow-hidden">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold">Components</h2>
            <Link
              to="/data-sources"
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-purple-100 text-purple-700 text-xs font-medium hover:bg-purple-200 transition-colors"
              title="Click to change data source"
            >
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
              </svg>
              Data: {activeDataSource?.name || 'Yahoo Finance'}
            </Link>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAddComponentDialog(true)}
            >
              + Add Component
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRunBacktest}
              disabled={!index?.components?.length}
              title={!index?.components?.length ? 'Add components first' : ''}
            >
              <Play className="h-4 w-4 mr-2" />
              Run Backtest
            </Button>
          </div>
        </div>
        {index.components?.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            No components added yet
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Ticker</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Name</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">Sector</th>
                <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Market Cap</th>
                <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">Weight</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {index.components?.map((component: any) => (
                <tr key={component.id} className="hover:bg-muted/50">
                  <td className="px-6 py-4 font-mono font-medium">{component.ticker}</td>
                  <td className="px-6 py-4">{component.name || '-'}</td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">{component.sector || '-'}</td>
                  <td className="px-6 py-4 text-right">{component.market_cap ? formatMarketCap(component.market_cap) : '-'}</td>
                  <td className="px-6 py-4 text-right font-medium">{formatPercent(component.weight)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Backtest Dialog */}
      {showBacktestDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Run Backtest</h2>
              <button onClick={() => setShowBacktestDialog(false)} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Backtest Name</label>
                <input
                  type="text"
                  value={backtestName}
                  onChange={(e) => setBacktestName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="My Backtest"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={backtestStartDate}
                    onChange={(e) => setBacktestStartDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                  <input
                    type="date"
                    value={backtestEndDate}
                    onChange={(e) => setBacktestEndDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Benchmark (optional)</label>
                <input
                  type="text"
                  value={backtestBenchmark}
                  onChange={(e) => setBacktestBenchmark(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="SPY"
                />
                <p className="text-xs text-gray-500 mt-1">Enter a ticker symbol to compare against (e.g., SPY, QQQ)</p>
              </div>

              {backtestMutation.isError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">
                  {(backtestMutation.error as any)?.response?.data?.detail || 'Failed to create backtest'}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowBacktestDialog(false)}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={submitBacktest}
                  disabled={backtestMutation.isPending || !backtestName || !backtestStartDate || !backtestEndDate}
                >
                  {backtestMutation.isPending ? 'Running...' : 'Run Backtest'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Component Dialog */}
      {showAddComponentDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Add Component</h2>
              <button onClick={() => setShowAddComponentDialog(false)} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ticker Symbol</label>
                <input
                  type="text"
                  value={newComponentTicker}
                  onChange={(e) => setNewComponentTicker(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 uppercase"
                  placeholder="AAPL"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Weight</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={newComponentWeight}
                  onChange={(e) => setNewComponentWeight(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">Enter as decimal (e.g., 0.10 for 10%)</p>
              </div>

              {addComponentMutation.isError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">
                  {(addComponentMutation.error as any)?.response?.data?.detail || 'Failed to add component'}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowAddComponentDialog(false)}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={submitAddComponent}
                  disabled={addComponentMutation.isPending || !newComponentTicker}
                >
                  {addComponentMutation.isPending ? 'Adding...' : 'Add Component'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

